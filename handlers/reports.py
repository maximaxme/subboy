"""
handlers/reports.py — Subscription expense reports.

Provides:
- "📊 Отчёты" menu
- "📅 Этот месяц" / "📆 Следующий месяц" forecasts
- "📆 Год" report (actual spend from payment history + annual projection)
- "💰 Ежемесячные расходы" summary
- "🧾 История платежей" with per-payment delete
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
from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Payment, Subscription
from utils.formatting import (
    RU_MONTHS_GEN,
    RU_MONTHS_NOM,
    fmt_money,
    fmt_price,
    fmt_subscription_price,
)

router = Router()

HISTORY_LIMIT = 30


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
            [InlineKeyboardButton(text="📆 Год", callback_data="report_year")],
            [InlineKeyboardButton(text="💰 Ежемесячные расходы", callback_data="report_monthly_total")],
            [InlineKeyboardButton(text="🧾 История платежей", callback_data="report_history")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")],
        ]
    )


def back_to_reports_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ К отчётам", callback_data="reports")],
        ]
    )


def history_keyboard(payments: list[Payment]) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for p in payments:
        label = f"{p.paid_on.strftime('%d.%m.%y')} · {p.name} · {fmt_money(p.amount, p.currency, p.amount_original)}"
        if len(label) > 60:
            label = label[:59] + "…"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"pay_view:{p.id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ К отчётам", callback_data="reports")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def payment_detail_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить из истории", callback_data=f"pay_del:{payment_id}")],
            [InlineKeyboardButton(text="⬅️ К истории", callback_data="report_history")],
        ]
    )


# ──────────────────────────────────────────────────────────────────────────────
# Data helpers
# ──────────────────────────────────────────────────────────────────────────────

async def _get_user_subs(session: AsyncSession, user_id: int) -> list[Subscription]:
    # Reports cover money actually due, so paused (is_active=False) subscriptions
    # are excluded — they show up separately in the subscriptions list, not here.
    result = await session.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id, Subscription.is_active.is_(True))
        .order_by(Subscription.next_payment)
    )
    return list(result.scalars().all())


async def _get_user_payments(
    session: AsyncSession, user_id: int, limit: int | None = None
) -> list[Payment]:
    stmt = (
        select(Payment)
        .where(Payment.user_id == user_id)
        .order_by(Payment.paid_on.desc(), Payment.id.desc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


def _build_month_report(subs: list[Subscription], year: int, month: int) -> str:
    today = date.today()
    is_current = (year == today.year and month == today.month)
    is_future = year > today.year or (year == today.year and month > today.month)

    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    upcoming: list[tuple[date, Subscription]] = []
    passed: list[tuple[date, Subscription]] = []
    total = Decimal("0")

    for sub in subs:
        payment_date: date | None = None
        candidate = sub.next_payment

        if is_future:
            while candidate < first_day:
                if sub.period == "monthly":
                    candidate += relativedelta(months=1)
                else:
                    candidate += relativedelta(years=1)
            if first_day <= candidate <= last_day:
                payment_date = candidate
        else:
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
            lines.append(f"🔹 {d.day} {RU_MONTHS_GEN[d.month]} — {sub.name} — {fmt_subscription_price(sub)}")
        lines.append("")

    if passed:
        lines.append("Уже прошли:")
        for d, sub in passed:
            lines.append(f"✅ {d.day} {RU_MONTHS_GEN[d.month]} — {sub.name} — {fmt_subscription_price(sub)}")
        lines.append("")

    if not upcoming and not passed:
        lines.append("Нет списаний в этом месяце.")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━")
    lines.append(f"💰 Всего за месяц: ~{fmt_price(total.quantize(Decimal('0.01')))} ₽")

    return "\n".join(lines)


def _build_monthly_total(subs: list[Subscription]) -> str:
    if not subs:
        return "У тебя пока нет активных подписок."

    total_monthly = sum((monthly_cost(s) for s in subs), Decimal("0"))
    total_yearly = total_monthly * 12

    lines = ["💰 <b>Ежемесячные расходы</b>\n"]
    for sub in sorted(subs, key=lambda s: monthly_cost(s), reverse=True):
        mc = monthly_cost(sub)
        period_sym = "мес" if sub.period == "monthly" else "год"
        lines.append(
            f"🔹 {sub.name} — {fmt_subscription_price(sub)}/{period_sym}"
            + (f" (~{fmt_price(mc.quantize(Decimal('0.01')))} ₽/мес)" if sub.period == "yearly" else "")
        )

    lines.append("\n━━━━━━━━━━━━━━━")
    lines.append(f"📊 В месяц: ~{fmt_price(total_monthly.quantize(Decimal('0.01')))} ₽")
    lines.append(f"📆 В год: ~{fmt_price(total_yearly.quantize(Decimal('0.01')))} ₽")
    return "\n".join(lines)


def _build_year_report(subs: list[Subscription], payments: list[Payment], year: int) -> str:
    by_month: dict[int, Decimal] = {}
    actual_total = Decimal("0")
    for p in payments:
        if p.paid_on.year != year:
            continue
        by_month[p.paid_on.month] = by_month.get(p.paid_on.month, Decimal("0")) + p.amount
        actual_total += p.amount

    projected_annual = sum((monthly_cost(s) for s in subs), Decimal("0")) * 12

    lines = [f"📆 <b>Расходы за {year}</b>\n"]
    lines.append(f"✅ Фактически потрачено: ~{fmt_price(actual_total.quantize(Decimal('0.01')))} ₽")

    if by_month:
        lines.append("\nПо месяцам:")
        for m in range(1, 13):
            if m in by_month:
                lines.append(f"🔹 {RU_MONTHS_NOM[m]} — ~{fmt_price(by_month[m].quantize(Decimal('0.01')))} ₽")
    else:
        lines.append("История платежей пока пуста — она наполняется по мере списаний.")

    lines.append("\n━━━━━━━━━━━━━━━")
    lines.append(
        f"📈 Прогноз на год по активным подпискам: ~{fmt_price(projected_annual.quantize(Decimal('0.01')))} ₽"
    )
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
    await callback.message.edit_text(text, reply_markup=back_to_reports_keyboard(), parse_mode="HTML")
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
    await callback.message.edit_text(text, reply_markup=back_to_reports_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "report_year")
async def report_year(callback: CallbackQuery, session: AsyncSession) -> None:
    today = date.today()
    subs = await _get_user_subs(session, callback.from_user.id)
    payments = await _get_user_payments(session, callback.from_user.id)
    text = _build_year_report(subs, payments, today.year)
    await callback.message.edit_text(text, reply_markup=back_to_reports_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "report_monthly_total")
async def report_monthly_total(callback: CallbackQuery, session: AsyncSession) -> None:
    subs = await _get_user_subs(session, callback.from_user.id)
    text = _build_monthly_total(subs)
    await callback.message.edit_text(text, reply_markup=back_to_reports_keyboard(), parse_mode="HTML")
    await callback.answer()


# ──────────────────────────────────────────────────────────────────────────────
# Payment history
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "report_history")
async def report_history(callback: CallbackQuery, session: AsyncSession) -> None:
    payments = await _get_user_payments(session, callback.from_user.id, limit=HISTORY_LIMIT)
    if not payments:
        await callback.message.edit_text(
            "🧾 <b>История платежей</b>\n\n"
            "Пока пусто. История наполняется автоматически по мере списаний по подпискам.",
            reply_markup=back_to_reports_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    total = sum((p.amount for p in payments), Decimal("0"))
    text = (
        "🧾 <b>История платежей</b>\n\n"
        f"Последние {len(payments)} записей (на ~{fmt_price(total.quantize(Decimal('0.01')))} ₽).\n"
        "Нажми на запись, чтобы посмотреть или удалить."
    )
    await callback.message.edit_text(text, reply_markup=history_keyboard(payments), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("pay_view:"))
async def payment_view(callback: CallbackQuery, session: AsyncSession) -> None:
    payment_id = int(callback.data.split(":")[1])
    payment = await session.get(Payment, payment_id)
    if not payment or payment.user_id != callback.from_user.id:
        await callback.answer("Платёж не найден.", show_alert=True)
        return

    text = (
        "🧾 <b>Платёж</b>\n\n"
        f"📝 {payment.name}\n"
        f"💰 {fmt_money(payment.amount, payment.currency, payment.amount_original)}\n"
        f"📅 {payment.paid_on.strftime('%d.%m.%Y')}"
    )
    await callback.message.edit_text(text, reply_markup=payment_detail_keyboard(payment_id), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("pay_del:"))
async def payment_delete(callback: CallbackQuery, session: AsyncSession) -> None:
    payment_id = int(callback.data.split(":")[1])
    payment = await session.get(Payment, payment_id)
    if not payment or payment.user_id != callback.from_user.id:
        await callback.answer("Платёж не найден.", show_alert=True)
        return

    await session.delete(payment)
    await session.commit()
    await callback.answer("Запись удалена 🗑")

    payments = await _get_user_payments(session, callback.from_user.id, limit=HISTORY_LIMIT)
    if not payments:
        await callback.message.edit_text(
            "🧾 <b>История платежей</b>\n\nПусто.",
            reply_markup=back_to_reports_keyboard(),
            parse_mode="HTML",
        )
        return

    total = sum((p.amount for p in payments), Decimal("0"))
    text = (
        "🧾 <b>История платежей</b>\n\n"
        f"Последние {len(payments)} записей (на ~{fmt_price(total.quantize(Decimal('0.01')))} ₽).\n"
        "Нажми на запись, чтобы посмотреть или удалить."
    )
    await callback.message.edit_text(text, reply_markup=history_keyboard(payments), parse_mode="HTML")
