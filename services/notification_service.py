"""
services/notification_service.py — Handles all billing reminder notifications.

Logic:
- Called by the scheduler every hour.
- For each user with notifications enabled:
    - Find subscriptions where next_billing_date == today + notify_days_before
    - Send a Telegram message for each such subscription
- Gracefully handles errors per-user so one failure doesn't block others.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Subscription

logger = logging.getLogger(__name__)


async def send_billing_reminders(bot: Bot, session: AsyncSession) -> None:
    """
    Main entry point called by the scheduler.
    Sends billing reminder messages to all eligible users.
    """
    today = date.today()
    logger.info("Running billing reminders for %s", today)

    # Load all users with notifications enabled
    result = await session.execute(
        select(User).where(User.notifications_enabled == True)  # noqa: E712
    )
    users: list[User] = result.scalars().all()
    logger.info("Found %d users with notifications enabled", len(users))

    for user in users:
        try:
            await _notify_user(bot, session, user, today)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to notify user %d: %s", user.telegram_id, exc)


async def _notify_user(
    bot: Bot,
    session: AsyncSession,
    user: User,
    today: date,
) -> None:
    """Send reminders for a single user."""
    remind_date = today + timedelta(days=user.notify_days_before)

    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == user.telegram_id,
            Subscription.is_active == True,  # noqa: E712
            Subscription.next_billing_date == remind_date,
        )
    )
    subs: list[Subscription] = result.scalars().all()

    if not subs:
        return

    for sub in subs:
        cat_name = sub.category.name if sub.category else "—"
        text = (
            f"🔔 <b>Billing Reminder</b>\n\n"
            f"  Subscription: <b>{sub.name}</b>\n"
            f"  Amount:       {sub.amount:.2f} {sub.currency}\n"
            f"  Category:     {cat_name}\n"
            f"  Billing date: {sub.next_billing_date} "
            f"(in {user.notify_days_before} day(s))\n"
        )
        await bot.send_message(chat_id=user.telegram_id, text=text)
        logger.info(
            "Notified user %d about subscription '%s'",
            user.telegram_id,
            sub.name,
        )
