"""
handlers/categories.py — Category management (create, list, delete).
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Category, Subscription
from utils.states import ManageCategories

router = Router()


def categories_keyboard(cats: list[Category]) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for cat in cats:
        buttons.append(
            [
                InlineKeyboardButton(text=cat.name, callback_data=f"cat_detail:{cat.id}"),
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="➕ Новая категория", callback_data="add_category")]
    )
    buttons.append(
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cat_detail_keyboard(cat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить категорию", callback_data=f"delete_cat_ask:{cat_id}")],
            [InlineKeyboardButton(text="⬅️ К категориям", callback_data="categories")],
        ]
    )


def cat_delete_confirm_keyboard(cat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_cat_confirm:{cat_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"cat_detail:{cat_id}"),
            ]
        ]
    )


async def _get_user_cats(session: AsyncSession, user_id: int) -> list[Category]:
    result = await session.execute(
        select(Category).where(Category.user_id == user_id).order_by(Category.name)
    )
    return list(result.scalars().all())


@router.callback_query(F.data == "categories")
async def show_categories(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    cats = await _get_user_cats(session, callback.from_user.id)
    if cats:
        text = "🗂 <b>Твои категории:</b>\n\nНажми на категорию для управления."
    else:
        text = (
            "🗂 <b>Категории</b>\n\n"
            "У тебя пока нет категорий.\n"
            "Создай первую, нажав <b>➕ Новая категория</b>."
        )
    await callback.message.edit_text(
        text,
        reply_markup=categories_keyboard(cats),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat_detail:"))
async def show_cat_detail(callback: CallbackQuery, session: AsyncSession) -> None:
    cat_id = int(callback.data.split(":")[1])
    cat = await session.get(Category, cat_id)
    if not cat or cat.user_id != callback.from_user.id:
        await callback.answer("Категория не найдена.", show_alert=True)
        return

    # Count subscriptions in this category
    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == callback.from_user.id,
            Subscription.category_id == cat_id,
        )
    )
    subs = list(result.scalars().all())
    subs_count = len(subs)

    await callback.message.edit_text(
        f"🗂 <b>{cat.name}</b>\n\n"
        f"Подписок в категории: {subs_count}",
        reply_markup=cat_detail_keyboard(cat_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "add_category")
async def add_category_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ManageCategories.name)
    await callback.message.edit_text(
        "🗂 Введи название новой категории:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Отмена", callback_data="categories")]]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(StateFilter(ManageCategories.name))
async def add_category_save(message: Message, state: FSMContext, session: AsyncSession) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("Название не может быть пустым. Введи название категории:")
        return

    # Check for duplicates
    result = await session.execute(
        select(Category).where(
            Category.user_id == message.from_user.id,
            Category.name == name,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        await message.answer(
            f"Категория <b>{name}</b> уже существует. Введи другое название:",
            parse_mode="HTML",
        )
        return

    cat = Category(user_id=message.from_user.id, name=name)
    session.add(cat)
    await session.commit()
    await state.clear()

    cats = await _get_user_cats(session, message.from_user.id)
    await message.answer(
        f"✅ Категория <b>{name}</b> создана.\n\n🗂 <b>Твои категории:</b>",
        reply_markup=categories_keyboard(cats),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("delete_cat_ask:"))
async def delete_cat_ask(callback: CallbackQuery, session: AsyncSession) -> None:
    cat_id = int(callback.data.split(":")[1])
    cat = await session.get(Category, cat_id)
    if not cat or cat.user_id != callback.from_user.id:
        await callback.answer("Категория не найдена.", show_alert=True)
        return

    await callback.message.edit_text(
        f"🗑 Удалить категорию <b>{cat.name}</b>?\n\n"
        "Подписки из категории не удаляются — они просто останутся без категории.",
        reply_markup=cat_delete_confirm_keyboard(cat_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_cat_confirm:"))
async def delete_cat_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    cat_id = int(callback.data.split(":")[1])
    cat = await session.get(Category, cat_id)
    if not cat or cat.user_id != callback.from_user.id:
        await callback.answer("Категория не найдена.", show_alert=True)
        return

    # Detach subscriptions from this category
    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == callback.from_user.id,
            Subscription.category_id == cat_id,
        )
    )
    for sub in result.scalars().all():
        sub.category_id = None

    name = cat.name
    await session.delete(cat)
    await session.commit()

    cats = await _get_user_cats(session, callback.from_user.id)
    await callback.message.edit_text(
        f"✅ Категория <b>{name}</b> удалена.\n\n🗂 <b>Твои категории:</b>",
        reply_markup=categories_keyboard(cats),
        parse_mode="HTML",
    )
    await callback.answer()
