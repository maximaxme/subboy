"""
handlers/reports.py — Subscription expense reports.

Provides:
- "📊 Отчёты" menu
- "📅 Этот месяц" quick report
- "📆 Следующий месяц" report
- "💰 Всего за всё время" summary
"""
from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Subscription

router = Router()

# ──────────────────────────────────────────────────────────────────────────────
# Locale helpers
# ──────────────────────────────────────────────────────────────────────────────

RU_MONTHS_NOM = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]

RU_MONTHS_GEN = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]

RU_DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def fmt_price(price: Decimal) -> str:
    integer_part = int(price)
    frac = int(round((price - integer_part) * 100))
    s = f"{integer_part:,}".replace(",", "\u00a0")
    return f"{s}.{frac:02d}"


def monthly_cost(sub: Subscription) -> Decimal:
    if sub.period == "monthly":
        return sub.price
    return sub.price / 12


# ──────────────────────────────────────────────────────────────────────────────
# Keyboards
# ──────────────────────────────────────────────────────────────────────────────

def reports_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Этот месяц", callback_data="report_this_month")],
            [InlineKeyboardButton(text="📆 Следующий месяц", callback_data="report_next_month")],
            [InlineKeyboardButton(text="💰 Ежемесячные расходы", callback_data="report_monthly_total")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")],
        ]
    )


def back_to_reports_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ К отчётам", callback_data="reports")],
        ]
    )


# ──────────────────────────────────────────────────────────────────────────────
# Data helpers
# ──────────────────────────────────────────────────────────────────────────────

async def _get_user_subs(session: AsyncSession, user_id: int) -> list[Subscription]:
    result = await session.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.next_payment)
    )
    return list(result.scalars().all())


def _subs_in_month(subs: list[Subscription], year: int, month: int) -> tuple[list[Subscription], list[Subscription]]:
    """Split subscriptions into (upcoming, already_passed) for the given year/month."""
    today = date.today()
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    upcoming: list[Subscription] = []
    passed: list[Subscription] = []

    for sub in subs:
        # Check if next_payment falls in [first_day, last_day]
        np = sub.next_payment
        if first_day <= np <= last_day:
            if np < today or (year < today.year) or (year == today.year and month < today.month):
                passed.append(sub)
            else:
                upcoming.append(sub)
        # For past months — all subs that *would have* been due
        # For future months — estimate based on period
        elif year > today.year or (year == today.year and month > today.month):
            # Future month — use period to estimate
            sub_np = sub.next_payment
            while sub_np < first_day:
                if sub.period == "monthly":
                    from dateutil.relativedelta import relativedelta as rd
                    sub_np = sub_np + rd(months=1)
                else:
                    from dateutil.relativedelta import relativedelta as rd
                    sub_np = sub_np + rd(years=1)
            if first_day <= sub_np <= last_day:
                upcoming.append(sub)

    return upcoming, passed


def _build_month_report(
    subs: list[Subscription],
    year: int,
    month: int,
) -> str:
    today = date.today()
    is_current = (year == today.year and month == today.month)
    is_future = year > today.year or (year == today.year and month > today.month)

    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    upcoming: list[tuple[date, Subscription]] = []
    passed: list[tuple[date, Subscription]] = []
    total = Decimal("0")

    for sub in subs:
        # Find the payment date for this month
        payment_date: date | None = None
        candidate = sub.next_payment

        if is_future:
            # Advance candidate to target month
            from dateutil.relativedelta import relativedelta as rd
            while candidate < first_day:
                if sub.period == "monthly":
                    candidate += rd(months=1)
                else:
                    candidate += rd(years=1)
            if first_day <= candidate <= last_day:
                payment_date = candidate
        else:
            # Current or past month: use stored next_payment if in range, else skip
            if first_day <= candidate <= last_day:
                payment_date = candidate

        if payment_date is None:
            continue

        total += sub.price

        if is_current and payment_date < today:
            passed.append((payment_date, sub))
        else:
            upcoming.append((payment_date, sub))

    upcoming.sort(key=lambda x: x[0])
    passed.sort(key=lambda x: x[0])

    month_title = f"{RU_MONTHS_NOM[month]} {year}"
    lines = [f"📅 <b>{month_title}</b>\n"]

    if upcoming:
        lines.append("Предстоящие списания:")
        for d, sub in upcoming:
            lines.append(f"🔹 {d.day} {RU_MONTHS_GEN[d.month]} — {sub.name} — {fmt_price(sub.price)} ₽")
        lines.append("")

    if passed:
        lines.append("Уже прошли:")
        for d, sub in passed:
            lines.append(f"✅ {d.day} {RU_MONTHS_GEN[d.month]} — {sub.name} — {fmt_price(sub.price)} ₽")
        lines.append("")

    if not upcoming and not passed:
        lines.append("Нет списаний в этом месяце.")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━")
    lines.append(f"💰 Всего за месяц: ~{fmt_price(total.quantize(Decimal('0.01')))} ₽")

    return "\n".join(lines)


def _build_monthly_total(subs: list[Subscription]) -> str:
    if not subs:
        return "У тебя пока нет подписок."

    total_monthly = sum(monthly_cost(s) for s in subs)
    total_yearly = total_monthly * 12

    lines = [
        "💰 <b>Ежемесячные расходы</b>\n",
    ]
    for sub in sorted(subs, key=lambda s: monthly_cost(s), reverse=True):
        mc = monthly_cost(sub)
        period_sym = "мес" if sub.period == "monthly" else "год"
        lines.append(
            f"🔹 {sub.name} — {fmt_price(sub.price)} ₽/{period_sym}"
            + (f" (~{fmt_price(mc.quantize(Decimal('0.01')))} ₽/мес)" if sub.period == "yearly" else "")
        )

    lines.append("\n━━━━━━━━━━━━━━━")
    lines.append(f"📊 В месяц: ~{fmt_price(total_monthly.quantize(Decimal('0.01')))} ₽")
    lines.append(f"📆 В год: ~{fmt_price(total_yearly.quantize(Decimal('0.01')))} ₽")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Handlers
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "reports")
async def show_reports_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📊 <b>Отчёты</b>\n\nВыбери тип отчёта:",
        reply_markup=reports_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "report_this_month")
async def report_this_month(callback: CallbackQuery, session: AsyncSession) -> None:
    today = date.today()
    subs = await _get_user_subs(session, callback.from_user.id)
    text = _build_month_report(subs, today.year, today.month)
    await callback.message.edit_text(
        text,
        reply_markup=back_to_reports_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "report_next_month")
async def report_next_month(callback: CallbackQuery, session: AsyncSession) -> None:
    today = date.today()
    if today.month == 12:
        year, month = today.year + 1, 1
    else:
        year, month = today.year, today.month + 1

    subs = await _get_user_subs(session, callback.from_user.id)
    text = _build_month_report(subs, year, month)
    await callback.message.edit_text(
        text,
        reply_markup=back_to_reports_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "report_monthly_total")
async def report_monthly_total(callback: CallbackQuery, session: AsyncSession) -> None:
    subs = await _get_user_subs(session, callback.from_user.id)
    text = _build_monthly_total(subs)
    await callback.message.edit_text(
        text,
        reply_markup=back_to_reports_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()
