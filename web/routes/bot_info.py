"""Публичный эндпоинт: username бота для виджета Login with Telegram."""
from fastapi import APIRouter
from aiogram import Bot
from config import config

router = APIRouter(prefix="/bot", tags=["bot"])


@router.get("/username")
async def get_bot_username():
    """Возвращает @username бота (без @) для подстановки в Telegram Login Widget."""
    bot = Bot(token=config.BOT_TOKEN.get_secret_value())
    try:
        me = await bot.get_me()
        return {"username": me.username or ""}
    finally:
        await bot.session.close()
