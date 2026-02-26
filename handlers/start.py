from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from services.user_service import get_or_create_user

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message, session: AsyncSession):
    await get_or_create_user(
        session=session,
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ Добавить подписку", callback_data="add_sub"))
    kb.row(types.InlineKeyboardButton(text="📋 Мои подписки", callback_data="my_subs"))
    kb.row(types.InlineKeyboardButton(text="🗂 Категории", callback_data="categories"))
    kb.row(types.InlineKeyboardButton(text="📊 Отчёты", callback_data="reports"))
    kb.row(types.InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"))

    await message.answer(
        "👋 Привет!\n"
        "Я помогу следить за подписками и не забывать про списания.\n\n"
        "Начнём?",
        reply_markup=kb.as_markup()
    )

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, session: AsyncSession):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ Добавить подписку", callback_data="add_sub"))
    kb.row(types.InlineKeyboardButton(text="📋 Мои подписки", callback_data="my_subs"))
    kb.row(types.InlineKeyboardButton(text="🗂 Категории", callback_data="categories"))
    kb.row(types.InlineKeyboardButton(text="📊 Отчёты", callback_data="reports"))
    kb.row(types.InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"))

    await callback.message.edit_text(
        "👋 Привет!\n"
        "Я помогу следить за подписками и не забывать про списания.\n\n"
        "Начнём?",
        reply_markup=kb.as_markup()
    )
    await callback.answer()
