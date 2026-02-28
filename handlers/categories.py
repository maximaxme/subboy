"""
handlers/categories.py — Category management (create, list, rename, delete).
"""
from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Category, Subscription
from utils.states import CategoryStates

logger = logging.getLogger(__name__)
router = Router(name="categories")


# ─── Helpers ───────────────────────────────────────────────────────────────────


def _categories_keyboard(categories: list[Category]) -> InlineKeyboardMarkup:
    rows = []
    for cat in categories:
        rows.append([
            InlineKeyboardButton(text=cat.name,          callback_data=f"cat:view:{cat.id}"),
            InlineKeyboardButton(text="✏️ Rename",        callback_data=f"cat:rename:{cat.id}"),
            InlineKeyboardButton(text="🗑 Delete",         callback_data=f"cat:delete:{cat.id}"),
        ])
    rows.append([InlineKeyboardButton(text="➕ New Category", callback_data="cat:new")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _send_categories(target: Message | CallbackQuery, session: AsyncSession) -> None:
    """Send or edit the categories list."""
    if isinstance(target, CallbackQuery):
        user_id = target.from_user.id
        send = target.message.edit_text
    else:
        user_id = target.from_user.id
        send = target.answer

    result = await session.execute(
        select(Category).where(Category.user_id == user_id).order_by(Category.name)
    )
    categories = result.scalars().all()

    if not categories:
        text = "You have no categories yet. Create one!"
    else:
        text = "<b>Your Categories</b>\n\n" + "\n".join(f"  • {c.name}" for c in categories)

    await send(text, reply_markup=_categories_keyboard(categories))


# ─── Entry ─────────────────────────────────────────────────────────────────────


@router.message(Command("categories"))
@router.message(F.text == "🏷 Categories")
async def cmd_categories(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    await _send_categories(message, session)


# ─── View ──────────────────────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("cat:view:"))
async def cb_cat_view(callback: CallbackQuery, session: AsyncSession) -> None:
    cat_id = int(callback.data.split(":")[2])
    cat = await session.get(Category, cat_id)
    if not cat or cat.user_id != callback.from_user.id:
        await callback.answer("Not found.", show_alert=True)
        return
    result = await session.execute(
        select(Subscription).where(Subscription.category_id == cat_id)
    )
    subs = result.scalars().all()
    sub_list = "\n".join(f"    – {s.name}" for s in subs) or "    (none)"
    await callback.answer(
        f"{cat.name}\nSubscriptions:\n{sub_list}",
        show_alert=True,
    )


# ─── New ───────────────────────────────────────────────────────────────────────


@router.callback_query(F.data == "cat:new")
async def cb_cat_new(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CategoryStates.waiting_name)
    await callback.message.answer("Enter a name for the new category:")
    await callback.answer()


@router.message(CategoryStates.waiting_name)
async def cat_create(message: Message, state: FSMContext, session: AsyncSession) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("Name cannot be empty.")
        return
    cat = Category(user_id=message.from_user.id, name=name)
    session.add(cat)
    await session.commit()
    await state.clear()
    await message.answer(f"✅ Category <b>{name}</b> created!")
    await _send_categories(message, session)


# ─── Rename ────────────────────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("cat:rename:"))
async def cb_cat_rename_start(callback: CallbackQuery, state: FSMContext) -> None:
    cat_id = int(callback.data.split(":")[2])
    await state.set_state(CategoryStates.waiting_rename)
    await state.update_data(cat_id=cat_id)
    await callback.message.answer("Enter the new name for this category:")
    await callback.answer()


@router.message(CategoryStates.waiting_rename)
async def cat_rename(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    cat = await session.get(Category, data["cat_id"])
    if not cat or cat.user_id != message.from_user.id:
        await message.answer("Category not found.")
        await state.clear()
        return
    old_name = cat.name
    cat.name = message.text.strip()
    await session.commit()
    await state.clear()
    await message.answer(f"✅ Renamed <b>{old_name}</b> → <b>{cat.name}</b>")
    await _send_categories(message, session)


# ─── Delete ────────────────────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("cat:delete:"))
async def cb_cat_delete_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    cat_id = int(callback.data.split(":")[2])
    cat = await session.get(Category, cat_id)
    if not cat or cat.user_id != callback.from_user.id:
        await callback.answer("Not found.", show_alert=True)
        return
    await callback.message.answer(
        f"Delete category <b>{cat.name}</b>? Subscriptions in it will become uncategorised.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="✅ Yes",    callback_data=f"cat:del_confirm:{cat_id}"),
                InlineKeyboardButton(text="❌ Cancel", callback_data="cat:del_cancel"),
            ]]
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat:del_confirm:"))
async def cb_cat_delete_execute(callback: CallbackQuery, session: AsyncSession) -> None:
    cat_id = int(callback.data.split(":")[2])
    cat = await session.get(Category, cat_id)
    if cat and cat.user_id == callback.from_user.id:
        # Unlink subscriptions
        result = await session.execute(
            select(Subscription).where(Subscription.category_id == cat_id)
        )
        for sub in result.scalars().all():
            sub.category_id = None
        await session.delete(cat)
        await session.commit()
        await callback.message.edit_text(f"🗑 Category <b>{cat.name}</b> deleted.")
    await callback.answer()


@router.callback_query(F.data == "cat:del_cancel")
async def cb_cat_delete_cancel(callback: CallbackQuery) -> None:
    await callback.message.edit_text("Deletion cancelled.")
    await callback.answer()
