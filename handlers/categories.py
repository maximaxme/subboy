"""
handlers/categories.py — Category management (create, list, delete).
"""
from __future__ import annotations

from decimal import Decimal

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
from utils.formatting import fmt_price, fmt_subscription_price, monthly_cost
from utils.states import ManageCategories

router = Router()

# Virtual category for subscriptions without a category
OTHER_TITLE = "Разные"


def categories_keyboard(
    cats: list[Category], counts: dict[int, int], other_count: int
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for cat in cats:
        c = counts.get(cat.id, 0)
        buttons.append(
            [InlineKeyboardButton(text=f"🗂 {cat.name} ({c})", callback_data=f"cat_detail:{cat.id}")]
        )
    if other_count > 0:
        buttons.append(
            [InlineKeyboardButton(text=f"📦 {OTHER_TITLE} ({other_count})", callback_data="cat_other")]
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


def other_detail_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ К категориям", callback_data="categories")],
        ]
    )


def _build_category_text(title: str, emoji: str, subs: list[Subscription]) -> str:
    if not subs:
        return f"{emoji} <b>{title}</b>\n\nВ этой категории пока нет подписок."

    active = [s for s in subs if s.is_active]
    paused = [s for s in subs if not s.is_active]
    ordered = sorted(subs, key=lambda s: (not s.is_active, s.name.lower()))

    lines = [f"{emoji} <b>{title}</b>\n"]
    for s in ordered:
        period_sym = "мес" if s.period == "monthly" else "год"
        if s.is_active:
            lines.append(f"🟢 <b>{s.name}</b> — {fmt_subscription_price(s)}/{period_sym}")
        else:
            lines.append(f"⏸ <s>{s.name}</s> — {fmt_subscription_price(s)}/{period_sym} (пауза)")

    total_monthly = sum((monthly_cost(s) for s in active), Decimal("0"))
    total_yearly = total_monthly * 12

    lines.append("\n━━━━━━━━━━━━━━━")
    lines.append(f"Активных: {len(active)} · на паузе: {len(paused)}")
    lines.append(f"💰 В месяц: ~{fmt_price(total_monthly.quantize(Decimal('0.01')))} ₽")
    lines.append(f"📆 В год: ~{fmt_price(total_yearly.quantize(Decimal('0.01')))} ₽")
    return "\n".join(lines)


async def _subs_in_category(
    session: AsyncSession, user_id: int, cat_id: int | None
) -> list[Subscription]:
    stmt = select(Subscription).where(Subscription.user_id == user_id)
    if cat_id is None:
        stmt = stmt.where(Subscription.category_id.is_(None))
    else:
        stmt = stmt.where(Subscription.category_id == cat_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


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


async def _categories_markup(session: AsyncSession, user_id: int) -> InlineKeyboardMarkup:
    cats = await _get_user_cats(session, user_id)
    all_subs = (
        await session.execute(select(Subscription).where(Subscription.user_id == user_id))
    ).scalars().all()
    counts: dict[int, int] = {}
    other_count = 0
    for s in all_subs:
        if s.category_id is None:
            other_count += 1
        else:
            counts[s.category_id] = counts.get(s.category_id, 0) + 1
    return categories_keyboard(cats, counts, other_count)


@router.callback_query(F.data == "categories")
async def show_categories(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    cats = await _get_user_cats(session, callback.from_user.id)

    # Count subscriptions per category (+ uncategorized → "Разные")
    all_subs = (
        await session.execute(
            select(Subscription).where(Subscription.user_id == callback.from_user.id)
        )
    ).scalars().all()
    counts: dict[int, int] = {}
    other_count = 0
    for s in all_subs:
        if s.category_id is None:
            other_count += 1
        else:
            counts[s.category_id] = counts.get(s.category_id, 0) + 1

    if cats or other_count:
        text = "🗂 <b>Твои категории:</b>\n\nНажми на категорию, чтобы посмотреть подписки в ней."
    else:
        text = (
            "🗂 <b>Категории</b>\n\n"
            "У тебя пока нет категорий.\n"
            "Создай первую, нажав <b>➕ Новая категория</b>."
        )
    await callback.message.edit_text(
        text,
        reply_markup=categories_keyboard(cats, counts, other_count),
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

    subs = await _subs_in_category(session, callback.from_user.id, cat_id)
    await callback.message.edit_text(
        _build_category_text(cat.name, "🗂", subs),
        reply_markup=cat_detail_keyboard(cat_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "cat_other")
async def show_other_category(callback: CallbackQuery, session: AsyncSession) -> None:
    subs = await _subs_in_category(session, callback.from_user.id, None)
    await callback.message.edit_text(
        _build_category_text(OTHER_TITLE, "📦", subs),
        reply_markup=other_detail_keyboard(),
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

    await message.answer(
        f"✅ Категория <b>{name}</b> создана.\n\n🗂 <b>Твои категории:</b>",
        reply_markup=await _categories_markup(session, message.from_user.id),
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

    await callback.message.edit_text(
        f"✅ Категория <b>{name}</b> удалена.\n\n🗂 <b>Твои категории:</b>",
        reply_markup=await _categories_markup(session, callback.from_user.id),
        parse_mode="HTML",
    )
    await callback.answer()
