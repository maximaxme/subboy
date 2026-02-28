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

    # Scheduler for notifications
    scheduler = create_scheduler(
        bot=bot,
        session_factory=db_helper.session_factory,
    )
    scheduler.start()
    logger.info("Scheduler started.")

    try:
        logger.info("Starting bot...")
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        logger.info("Bot shut down cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception("Bot crashed: %s", e)
        sys.exit(1)
