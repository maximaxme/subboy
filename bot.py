"""
bot.py — Main entry point for Subboy Telegram bot.

Startup sequence:
1. Load config (pydantic settings)
2. Create Bot + Dispatcher
3. Register all handlers
4. Configure and start APScheduler
5. Start polling (blocks until shutdown)
6. On shutdown: stop scheduler gracefully
"""
from __future__ import annotations

import asyncio
import logging
import sys

# Fix for Windows event loop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database.db_helper import db_helper
from handlers import (
    start_router,
    subscriptions_router,
    categories_router,
    reports_router,
    settings_router,
)
from middlewares.db_session import DbSessionMiddleware
from services.scheduler import create_scheduler

# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

async def main() -> None:
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(start_router)
    dp.include_router(subscriptions_router)
    dp.include_router(categories_router)
    dp.include_router(reports_router)
    dp.include_router(settings_router)

    bot = Bot(
        token=config.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    scheduler = create_scheduler(bot)
    scheduler.start()
    logger.info("Scheduler started")

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
        await db_helper.dispose()


if __name__ == "__main__":
    asyncio.run(main())
