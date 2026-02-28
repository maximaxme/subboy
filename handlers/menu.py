"""
handlers/menu.py — Re-usable main menu helper (imported by other handlers).
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def build_main_menu() -> InlineKeyboardMarkup:
    """Return the main menu inline keyboard (re-exported for other modules)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Добавить подписку", callback_data="add_sub"),
            ],
            [
                InlineKeyboardButton(text="📋 Мои подписки", callback_data="my_subs"),
                InlineKeyboardButton(text="📊 Отчёты", callback_data="reports"),
            ],
            [
                InlineKeyboardButton(text="🗂 Категории", callback_data="categories"),
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"),
            ],
        ]
    )
