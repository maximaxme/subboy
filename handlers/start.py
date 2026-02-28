"""
handlers/start.py — /start command, /help command, main menu keyboard,
and the universal "back_to_main" callback.
"""
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext

from services.user_service import get_or_create_user

router = Router()


def build_main_menu() -> InlineKeyboardMarkup:
    """Return the main menu inline keyboard."""
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


WELCOME_TEXT = (
    "👋 Привет! Я <b>Subboy</b> — твой трекер подписок.\n\n"
    "Я помогу тебе:\n"
    "• отслеживать все подписки в одном месте\n"
    "• получать напоминания перед списанием\n"
    "• видеть, сколько ты тратишь в месяц\n\n"
    "Выбери действие ниже 👇"
)

HELP_TEXT = (
    "<b>Что умеет Subboy?</b>\n\n"
    "➕ <b>Добавить подписку</b> — укажи название, цену, период и дату следующего списания.\n\n"
    "📋 <b>Мои подписки</b> — список всех подписок, отсортированных по дате. "
    "Нажми на любую, чтобы посмотреть детали, изменить или удалить.\n\n"
    "📊 <b>Отчёты</b> — сводка расходов за текущий или произвольный месяц.\n\n"
    "🗂 <b>Категории</b> — создавай категории и группируй подписки.\n\n"
    "⚙️ <b>Настройки</b> — включи уведомления:\n"
    "   • за день до списания\n"
    "   • еженедельный дайджест (по понедельникам)\n"
    "   • ежемесячный отчёт\n\n"
    "Даты списания обновляются автоматически после каждого периода.\n\n"
    "Используй /start, чтобы вернуться в главное меню."
)


@router.message(CommandStart())
async def cmd_start(message: Message, session, state: FSMContext) -> None:
    """Handle /start — register user if new, show main menu."""
    await state.clear()
    await get_or_create_user(
        session=session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    await message.answer(WELCOME_TEXT, reply_markup=build_main_menu(), parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help — show feature overview."""
    await message.answer(HELP_TEXT, parse_mode="HTML")


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext) -> None:
    """Universal 'back to main menu' callback."""
    await state.clear()
    await callback.message.edit_text(
        WELCOME_TEXT,
        reply_markup=build_main_menu(),
        parse_mode="HTML",
    )
    await callback.answer()
