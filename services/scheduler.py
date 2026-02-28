"""
services/scheduler.py — APScheduler integration running inside the bot process.

Jobs:
  Daily at 09:00 UTC (12:00 Moscow):
    1. advance_past_due_payments — roll forward overdue subscription dates
    2. check_and_send_notifications — send "day before" reminders

  Every Monday at 09:00 UTC:
    3. send_weekly_digest — weekly payments digest

  1st of every month at 09:00 UTC:
    4. send_monthly_report — monthly expense summary

Usage in bot.py:
    from services.scheduler import create_scheduler
    scheduler = create_scheduler(bot=bot, session_factory=session_factory)
    scheduler.start()
    ...
    scheduler.shutdown()
"""
from __future__ import annotations

import logging
from typing import Callable

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from services.notification_service import (
    advance_past_due_payments,
    check_and_send_notifications,
    send_monthly_report,
    send_weekly_digest,
)

logger = logging.getLogger(__name__)


def create_scheduler(
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIOScheduler:
    """
    Create and configure the APScheduler instance.

    Call scheduler.start() after creation to begin the jobs.
    Call scheduler.shutdown() on application shutdown.
    """
    scheduler = AsyncIOScheduler(timezone="UTC")

    # ── Daily job: advance past-due dates + send day-before reminders ──────
    scheduler.add_job(
        _daily_job,
        trigger="cron",
        hour=9,
        minute=0,
        kwargs={"bot": bot, "session_factory": session_factory},
        id="daily_notifications",
        replace_existing=True,
    )

    # ── Weekly job: Monday digest ──────────────────────────────────────────
    scheduler.add_job(
        _weekly_job,
        trigger="cron",
        day_of_week="mon",
        hour=9,
        minute=0,
        kwargs={"bot": bot, "session_factory": session_factory},
        id="weekly_digest",
        replace_existing=True,
    )

    # ── Monthly job: 1st of every month ───────────────────────────────────
    scheduler.add_job(
        _monthly_job,
        trigger="cron",
        day=1,
        hour=9,
        minute=0,
        kwargs={"bot": bot, "session_factory": session_factory},
        id="monthly_report",
        replace_existing=True,
    )

    logger.info("Scheduler configured with 3 jobs (daily, weekly, monthly).")
    return scheduler


# ──────────────────────────────────────────────────────────────────────────────
# Job wrappers — each opens its own DB session
# ──────────────────────────────────────────────────────────────────────────────

async def _daily_job(bot: Bot, session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Advance past-due payments then send day-before reminders."""
    logger.info("Running daily job: advance_past_due_payments + check_and_send_notifications")
    async with session_factory() as session:
        try:
            advanced = await advance_past_due_payments(session)
            logger.info("Daily job: advanced %d subscription(s).", advanced)
        except Exception as exc:
            logger.error("Daily job — advance_past_due_payments failed: %s", exc, exc_info=True)

    async with session_factory() as session:
        try:
            await check_and_send_notifications(bot, session)
            logger.info("Daily job: notifications sent.")
        except Exception as exc:
            logger.error("Daily job — check_and_send_notifications failed: %s", exc, exc_info=True)


async def _weekly_job(bot: Bot, session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Send weekly digest to subscribed users."""
    logger.info("Running weekly digest job.")
    async with session_factory() as session:
        try:
            await send_weekly_digest(bot, session)
        except Exception as exc:
            logger.error("Weekly job failed: %s", exc, exc_info=True)


async def _monthly_job(bot: Bot, session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Send monthly expense report to subscribed users."""
    logger.info("Running monthly report job.")
    async with session_factory() as session:
        try:
            await send_monthly_report(bot, session)
        except Exception as exc:
            logger.error("Monthly job failed: %s", exc, exc_info=True)
