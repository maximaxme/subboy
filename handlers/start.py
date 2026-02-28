"""
handlers/start.py — /start command, /help command, main menu.
"""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from services.user_service import get_or_create_user
from .menu import send_main_menu

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Handle /start: register user if new, show main menu."""
    await state.clear()
    user: User = await get_or_create_user(
        session=session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    greeting = (
        f"👋 Welcome back, {message.from_user.first_name}!"
        if not user.is_new
        else f"👋 Hello, {message.from_user.first_name}! I'm Subboy — your subscription tracker."
    )
    await message.answer(greeting)
    await send_main_menu(message)


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext) -> None:
    """Show help text."""
    await state.clear()
    help_text = (
        "<b>Subboy — Subscription Tracker</b>\n\n"
        "Commands:\n"
        "/start — Main menu\n"
        "/help  — This message\n\n"
        "Use the buttons below to manage your subscriptions, "
        "view reports, and configure notifications."
    )
    await message.answer(help_text)
    await send_main_menu(message)
