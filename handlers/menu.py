"""
handlers/menu.py — Re-usable main menu helper.
"""
from __future__ import annotations

from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton


MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 My Subscriptions"), KeyboardButton(text="📊 Reports")],
        [KeyboardButton(text="🏷 Categories"),       KeyboardButton(text="⚙️ Settings")],
    ],
    resize_keyboard=True,
)


async def send_main_menu(message: Message, text: str = "Main menu:") -> None:
    await message.answer(text, reply_markup=MAIN_MENU)
