import asyncio
import logging
import sys

# Исправление для Windows - используем правильный event loop policy
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import config
from handlers import (
    start_router, 
    subscriptions_router, 
    categories_router, 
    reports_router,
    settings_router
)
from middlewares.db_session import DbSessionMiddleware

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    dp = Dispatcher()
    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(start_router)
    dp.include_router(subscriptions_router)
    dp.include_router(categories_router)
    dp.include_router(reports_router)
    dp.include_router(settings_router)

    bot = Bot(
        token=config.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    logging.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception("Bot crashed: %s", e)
        sys.exit(1)
