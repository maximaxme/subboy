"""
services/notification_service.py — Handles all scheduled notifications.

Three public async functions intended to be called by the scheduler:

1. advance_past_due_payments(session)
   - Finds subscriptions where next_payment < today
   - Advances by 1 month (monthly) or 1 year (yearly) until date is >= today
   - Called daily so dates are always current

2. check_and_send_notifications(bot, session)
   - For users with day_before=True: sends a reminder for subscriptions
     due TOMORROW
   - After advancing past-due payments the "tomorrow" subscriptions are
     always fresh

3. send_weekly_digest(bot, session)
   - For users with weekly=True: sends a digest of payments due in the
     next 7 days (called on Mondays)
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import NotificationSettings, Payment, Subscription, User
from utils.formatting import RU_DAYS_SHORT, RU_MONTHS_GEN, fmt_price, fmt_subscription_price

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Locale helpers
# ──────────────────────────────────────────────────────────────────────────────

def _advance_date(current: date, period: str) -> date:
    """Advance a date by one period (month or year)."""
    if period == "monthly":
        return current + relativedelta(months=1)
    elif period == "yearly":
        return current + relativedelta(years=1)
    else:
        # Fallback: treat unknown period as monthly
        return current + relativedelta(months=1)


# ──────────────────────────────────────────────────────────────────────────────
# 1. Advance past-due payments
# ──────────────────────────────────────────────────────────────────────────────

async def advance_past_due_payments(session: AsyncSession) -> int:
    """
    Find all subscriptions where next_payment < today and advance them
    forward period-by-period until next_payment >= today.

    Returns the count of subscriptions that were updated.
    """
    today = date.today()
    result = await session.execute(
        select(Subscription).where(
            Subscription.next_payment < today,
            Subscription.is_active.is_(True),
        )
    )
    subs = list(result.scalars().all())

    updated = 0
    for sub in subs:
        while sub.next_payment < today:
            # The charge happened on the old next_payment date — log it to history.
            session.add(Payment(
                user_id=sub.user_id,
                subscription_id=sub.id,
                name=sub.name,
                amount=sub.price,
                currency=sub.price_currency,
                amount_original=sub.price_original,
                paid_on=sub.next_payment,
            ))
            sub.next_payment = _advance_date(sub.next_payment, sub.period)
        updated += 1
        logger.info(
            "Advanced subscription id=%s (%s) next_payment to %s",
            sub.id, sub.name, sub.next_payment,
        )

    if updated:
        await session.commit()

    return updated


# ──────────────────────────────────────────────────────────────────────────────
# 2. Daily "day before" notifications
# ──────────────────────────────────────────────────────────────────────────────

async def check_and_send_notifications(bot: Bot, session: AsyncSession) -> None:
    """
    Send "⏰ Завтра списание" to users who have:
    - day_before=True in NotificationSettings
    - At least one subscription with next_payment == tomorrow
    """
    tomorrow = date.today() + timedelta(days=1)

    # Get all users with day_before enabled
    result = await session.execute(
        select(NotificationSettings).where(NotificationSettings.day_before.is_(True))
    )
    settings_list = list(result.scalars().all())

    for ns in settings_list:
        user_id = ns.user_id

        # Find subscriptions due tomorrow for this user
        sub_result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.is_active.is_(True),
                Subscription.next_payment == tomorrow,
            )
        )
        due_subs = list(sub_result.scalars().all())

        if not due_subs:
            continue

        # Subscriptions marked "always keep" get a plain reminder; the rest get an
        # interactive "still using this?" question (per subscription).
        plain_subs = [s for s in due_subs if s.always_keep]
        ask_subs = [s for s in due_subs if not s.always_keep]

        if plain_subs:
            lines: list[str] = ["⏰ <b>Завтра списание:</b>\n"]
            total = Decimal("0")
            for sub in plain_subs:
                lines.append(f"🔹 {sub.name} — {fmt_subscription_price(sub)}")
                total += sub.price
            if len(plain_subs) > 1:
                lines.append(f"\n💰 Итого завтра: {fmt_price(total.quantize(Decimal('0.01')))} ₽")
            try:
                await bot.send_message(user_id, "\n".join(lines), parse_mode="HTML")
                logger.info("Sent day_before notification to user %s", user_id)
            except Exception as exc:
                logger.warning("Failed to send notification to user %s: %s", user_id, exc)

        for sub in ask_subs:
            text = (
                "⏰ <b>Завтра списание</b>\n\n"
                f"🔹 {sub.name} — {fmt_subscription_price(sub)}\n\n"
                "Ты ещё пользуешься этой подпиской?"
            )
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Да, пользуюсь", callback_data=f"use_keep:{sub.id}")],
                    [InlineKeyboardButton(text="❌ Нет, не пользуюсь", callback_data=f"use_pause:{sub.id}")],
                    [InlineKeyboardButton(text="📌 Всегда пользуюсь, не спрашивать", callback_data=f"use_always:{sub.id}")],
                ]
            )
            try:
                await bot.send_message(user_id, text, reply_markup=keyboard, parse_mode="HTML")
                logger.info("Sent usage question to user %s for sub %s", user_id, sub.id)
            except Exception as exc:
                logger.warning("Failed to send usage question to user %s: %s", user_id, exc)


# ──────────────────────────────────────────────────────────────────────────────
# 3. Weekly digest (Mondays)
# ──────────────────────────────────────────────────────────────────────────────

async def send_weekly_digest(bot: Bot, session: AsyncSession) -> None:
    """
    Send a digest of payments due in the next 7 days to users with weekly=True.
    Intended to run every Monday.
    """
    today = date.today()
    week_end = today + timedelta(days=7)

    result = await session.execute(
        select(NotificationSettings).where(NotificationSettings.weekly.is_(True))
    )
    settings_list = list(result.scalars().all())

    for ns in settings_list:
        user_id = ns.user_id

        sub_result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.is_active.is_(True),
                Subscription.next_payment >= today,
                Subscription.next_payment <= week_end,
            ).order_by(Subscription.next_payment)
        )
        due_subs = list(sub_result.scalars().all())

        if not due_subs:
            continue

        lines: list[str] = ["📬 <b>Платежи на этой неделе:</b>\n"]
        total = Decimal("0")

        for sub in due_subs:
            day_name = RU_DAYS_SHORT[sub.next_payment.weekday()]
            day_num = sub.next_payment.day
            month_name = RU_MONTHS_GEN[sub.next_payment.month]
            lines.append(
                f"🔹 {day_name}, {day_num} {month_name} — {sub.name} — {fmt_subscription_price(sub)}"
            )
            total += sub.price

        lines.append(f"\n💰 Итого: ~{fmt_price(total.quantize(Decimal('0.01')))} ₽")

        text = "\n".join(lines)

        try:
            await bot.send_message(user_id, text, parse_mode="HTML")
            logger.info("Sent weekly digest to user %s", user_id)
        except Exception as exc:
            logger.warning("Failed to send weekly digest to user %s: %s", user_id, exc)


# ──────────────────────────────────────────────────────────────────────────────
# 4. Monthly report
# ──────────────────────────────────────────────────────────────────────────────

async def send_monthly_report(bot: Bot, session: AsyncSession) -> None:
    """
    Send a monthly expense summary to users with monthly=True.
    Intended to run on the 1st of every month.
    """
    result = await session.execute(
        select(NotificationSettings).where(NotificationSettings.monthly.is_(True))
    )
    settings_list = list(result.scalars().all())

    for ns in settings_list:
        user_id = ns.user_id

        sub_result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.is_active.is_(True),
            )
        )
        all_subs = list(sub_result.scalars().all())

        if not all_subs:
            continue

        total_monthly = sum(
            (s.price if s.period == "monthly" else s.price / 12)
            for s in all_subs
        )

        lines = [
            "📊 <b>Ежемесячный отчёт</b>\n",
            f"Всего подписок: {len(all_subs)}",
            f"💰 Ежемесячные расходы: ~{fmt_price(Decimal(str(total_monthly)).quantize(Decimal('0.01')))} ₽",
            "\nСамые дорогие:",
        ]
        for sub in sorted(all_subs, key=lambda s: s.price, reverse=True)[:5]:
            lines.append(f"🔹 {sub.name} — {fmt_subscription_price(sub)}")

        text = "\n".join(lines)

        try:
            await bot.send_message(user_id, text, parse_mode="HTML")
            logger.info("Sent monthly report to user %s", user_id)
        except Exception as exc:
            logger.warning("Failed to send monthly report to user %s: %s", user_id, exc)
