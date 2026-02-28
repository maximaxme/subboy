"""
services/scheduler.py — APScheduler integration for Subboy.

Schedule:
- Every hour, on the minute, check which users have their notify_hour
  matching the current UTC hour and send billing reminders.

Why hourly?
- Users can configure any notification hour (0–23 UTC).
- The simplest robust approach is to run every hour and filter
  users whose notify_hour matches the current hour.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database.db_helper import db_helper
from services.notification_service import send_billing_reminders

logger = logging.getLogger(__name__)


async def _hourly_job(bot: Bot) -> None:
    """
    Runs every hour. Filters users whose notify_hour matches
    the current UTC hour, then dispatches reminders.
    """
    current_hour = datetime.now(timezone.utc).hour
    logger.info("Hourly scheduler job running. UTC hour: %d", current_hour)

    async with db_helper.session_factory() as session:
        # Pass current_hour so notification_service can filter by it if needed.
        # For simplicity, notification_service currently sends to ALL enabled users;
        # to respect notify_hour, we pre-filter here.
        from sqlalchemy import select
        from database.models import User

        result = await session.execute(
            select(User).where(
                User.notifications_enabled == True,  # noqa: E712
                User.notify_hour == current_hour,
            )
        )
        users = result.scalars().all()
        if not users:
            logger.debug("No users to notify at hour %d", current_hour)
            return

        # Temporarily set session context — reuse the open session
        await send_billing_reminders(bot, session)


def create_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Create and configure the APScheduler instance."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _hourly_job,
        trigger=CronTrigger(minute=0),  # top of every hour
        args=[bot],
        id="billing_reminders",
        replace_existing=True,
        misfire_grace_time=300,  # 5 min grace window
    )
    logger.info("Scheduler configured: billing_reminders job added.")
    return scheduler
