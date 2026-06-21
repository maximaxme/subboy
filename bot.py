from __future__ import annotations

import asyncio
import logging
import os
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

SOCKS5_PROXY = os.getenv("SOCKS5_PROXY")


async def main() -> None:
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(start_router)
    dp.include_router(subscriptions_router)
    dp.include_router(categories_router)
    dp.include_router(reports_router)
    dp.include_router(settings_router)

    session = AiohttpSession(proxy=SOCKS5_PROXY) if SOCKS5_PROXY else AiohttpSession()
    bot = Bot(
        token=config.BOT_TOKEN.get_secret_value(),
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    scheduler = create_scheduler(
        bot=bot,
        session_factory=db_helper.session_factory,
    )
    scheduler.start()
    logger.info("Scheduler started. Telegram proxy: %s", SOCKS5_PROXY or "disabled")

    logger.info("Starting bot...")
    try:
        # Resilient polling: the Telegram connection goes through the WARP proxy,
        # whose route can briefly drop (ProxyError: Host unreachable). Instead of
        # crashing the whole process, wait and retry so the bot self-heals when the
        # route returns. SIGTERM makes start_polling return normally → clean exit.
        while True:
            try:
                await dp.start_polling(bot)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("Polling stopped with %r; retrying in 10s...", e)
                await asyncio.sleep(10)
                continue
            else:
                break
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
