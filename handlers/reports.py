"""
handlers/reports.py — Subscription expense reports.

Features:
- Monthly summary (current month, grouped by category)
- Yearly summary
- All-time total
- Per-category breakdown
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Subscription, Category

logger = logging.getLogger(__name__)
router = Router(name="reports")


# ─── Helpers ───────────────────────────────────────────────────────────────────


def _reports_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 This month",  callback_data="report:month")],
            [InlineKeyboardButton(text="📆 This year",   callback_data="report:year")],
            [InlineKeyboardButton(text="🏷 By category", callback_data="report:category")],
            [InlineKeyboardButton(text="🔢 All-time",    callback_data="report:alltime")],
        ]
    )


async def _get_active_subs(session: AsyncSession, user_id: int) -> list[Subscription]:
    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.is_active == True,  # noqa: E712
        )
    )
    return result.scalars().all()


def _monthly_cost(sub: Subscription) -> Decimal:
    """Normalise a subscription cost to a monthly equivalent."""
    cycle = sub.billing_cycle.lower()
    if cycle == "monthly":
        return sub.amount
    elif cycle == "yearly":
        return sub.amount / 12
    elif cycle == "weekly":
        return sub.amount * Decimal("4.33")
    elif cycle == "daily":
        return sub.amount * 30
    return sub.amount  # fallback


# ─── Entry ─────────────────────────────────────────────────────────────────────


@router.message(Command("reports"))
@router.message(F.text == "📊 Reports")
async def cmd_reports(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "<b>Expense Reports</b>\nChoose a report type:",
        reply_markup=_reports_keyboard(),
    )


# ─── Monthly ───────────────────────────────────────────────────────────────────


@router.callback_query(F.data == "report:month")
async def cb_report_month(callback: CallbackQuery, session: AsyncSession) -> None:
    user_id = callback.from_user.id
    today = date.today()
    subs = await _get_active_subs(session, user_id)

    total = Decimal("0")
    lines: list[str] = []
    for sub in subs:
        monthly = _monthly_cost(sub)
        total += monthly
        lines.append(f"  • {sub.name}: {monthly:.2f} {sub.currency}")

    text = (
        f"<b>📅 {today.strftime('%B %Y')} — Monthly Estimate</b>\n\n"
        + ("\n".join(lines) or "  No active subscriptions.")
        + f"\n\n<b>Total: {total:.2f}</b>"
    )
    await callback.message.edit_text(text, reply_markup=_reports_keyboard())
    await callback.answer()


# ─── Yearly ────────────────────────────────────────────────────────────────────


@router.callback_query(F.data == "report:year")
async def cb_report_year(callback: CallbackQuery, session: AsyncSession) -> None:
    user_id = callback.from_user.id
    today = date.today()
    subs = await _get_active_subs(session, user_id)

    total = Decimal("0")
    lines: list[str] = []
    for sub in subs:
        yearly = _monthly_cost(sub) * 12
        total += yearly
        lines.append(f"  • {sub.name}: {yearly:.2f} {sub.currency}")

    text = (
        f"<b>📆 {today.year} — Yearly Estimate</b>\n\n"
        + ("\n".join(lines) or "  No active subscriptions.")
        + f"\n\n<b>Total: {total:.2f}</b>"
    )
    await callback.message.edit_text(text, reply_markup=_reports_keyboard())
    await callback.answer()


# ─── By category ───────────────────────────────────────────────────────────────


@router.callback_query(F.data == "report:category")
async def cb_report_category(callback: CallbackQuery, session: AsyncSession) -> None:
    user_id = callback.from_user.id
    subs = await _get_active_subs(session, user_id)

    by_cat: dict[str, Decimal] = defaultdict(Decimal)
    for sub in subs:
        cat_name = sub.category.name if sub.category else "Uncategorised"
        by_cat[cat_name] += _monthly_cost(sub)

    lines = [
        f"  • {cat}: {amount:.2f}/mo"
        for cat, amount in sorted(by_cat.items(), key=lambda x: -x[1])
    ]
    text = (
        "<b>🏷 Monthly Cost by Category</b>\n\n"
        + ("\n".join(lines) or "  No active subscriptions.")
    )
    await callback.message.edit_text(text, reply_markup=_reports_keyboard())
    await callback.answer()


# ─── All-time ──────────────────────────────────────────────────────────────────


@router.callback_query(F.data == "report:alltime")
async def cb_report_alltime(callback: CallbackQuery, session: AsyncSession) -> None:
    user_id = callback.from_user.id
    result = await session.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subs = result.scalars().all()

    total_monthly = sum((_monthly_cost(s) for s in subs if s.is_active), Decimal("0"))
    total_subs = len(subs)
    active_subs = sum(1 for s in subs if s.is_active)

    text = (
        "<b>🔢 All-time Summary</b>\n\n"
        f"  Total subscriptions: {total_subs}\n"
        f"  Active: {active_subs}\n"
        f"  Paused: {total_subs - active_subs}\n\n"
        f"  <b>Monthly spend (active): {total_monthly:.2f}</b>\n"
        f"  <b>Yearly spend (active):  {total_monthly * 12:.2f}</b>"
    )
    await callback.message.edit_text(text, reply_markup=_reports_keyboard())
    await callback.answer()
