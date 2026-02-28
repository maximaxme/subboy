"""
handlers/subscriptions.py — Complete rewrite.

Features:
- Beautiful sorted subscription list with monthly total and nearest payment
- Clickable inline buttons per subscription → detail view
- Edit each field via FSM (name, price, period, next_payment, category)
- Delete with confirmation
- Add subscription via FSM (preserves original add_sub flow)
"""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Category, Subscription
from utils.states import AddSubscription, EditSubscription

router = Router()

# ──────────────────────────────────────────────────────────────────────────────
# Locale helpers
# ──────────────────────────────────────────────────────────────────────────────

RU_MONTHS_GEN = [
    "", "янв", "фев", "мар", "апр", "май", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек",
]

PERIOD_LABELS = {
    "monthly": "Ежемесячно",
    "yearly": "Ежегодно",
}


def fmt_price(price: Decimal) -> str:
    """Format price with space-thousands separator: 1 505.00"""
    integer_part = int(price)
    frac = int(round((price - integer_part) * 100))
    s = f"{integer_part:,}".replace(",", "\u00a0")  # non-breaking space
    return f"{s}.{frac:02d}"


def relative_days(target: date) -> str:
    """Return human-readable relative date string."""
    today = date.today()
    delta = (target - today).days
    if delta < 0:
        return "просрочено"
    if delta == 0:
        return "сегодня"
    if delta == 1:
        return "завтра"
    return f"через {delta} дней"


def short_date(d: date) -> str:
    """Return short date like '24 мар'."""
    return f"{d.day} {RU_MONTHS_GEN[d.month]}"


def full_date(d: date) -> str:
    """Return full date like '24.03.2026'."""
    return d.strftime("%d.%m.%Y")


# ──────────────────────────────────────────────────────────────────────────────
# Keyboards
# ──────────────────────────────────────────────────────────────────────────────

def subs_list_keyboard(subs: list[Subscription]) -> InlineKeyboardMarkup:
    """One button per subscription + back."""
    buttons = [
        [InlineKeyboardButton(text=sub.name, callback_data=f"sub_detail:{sub.id}")]
        for sub in subs
    ]
    buttons.append(
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def sub_detail_keyboard(sub_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Изменить название", callback_data=f"edit_sub_name:{sub_id}")],
            [InlineKeyboardButton(text="Изменить цену", callback_data=f"edit_sub_price:{sub_id}")],
            [InlineKeyboardButton(text="Изменить период", callback_data=f"edit_sub_period:{sub_id}")],
            [InlineKeyboardButton(text="Изменить дату списания", callback_data=f"edit_sub_date:{sub_id}")],
            [InlineKeyboardButton(text="Изменить категорию", callback_data=f"edit_sub_cat:{sub_id}")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_sub_ask:{sub_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="my_subs")],
        ]
    )


def period_keyboard(sub_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Ежемесячно", callback_data=f"set_period:monthly:{sub_id}"),
                InlineKeyboardButton(text="📆 Ежегодно", callback_data=f"set_period:yearly:{sub_id}"),
            ],
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data=f"sub_detail:{sub_id}")],
        ]
    )


def add_period_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Ежемесячно", callback_data="set_add_period:monthly"),
                InlineKeyboardButton(text="📆 Ежегодно", callback_data="set_add_period:yearly"),
            ],
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="back_to_main")],
        ]
    )


def delete_confirm_keyboard(sub_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_sub_confirm:{sub_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"sub_detail:{sub_id}"),
            ]
        ]
    )


# ──────────────────────────────────────────────────────────────────────────────
# Subscription list helpers
# ──────────────────────────────────────────────────────────────────────────────

async def _get_user_subs(session: AsyncSession, user_id: int) -> list[Subscription]:
    result = await session.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.next_payment)
    )
    return list(result.scalars().all())


async def _get_user_categories(session: AsyncSession, user_id: int) -> dict[int, str]:
    result = await session.execute(
        select(Category).where(Category.user_id == user_id)
    )
    return {c.id: c.name for c in result.scalars().all()}


def _build_list_text(subs: list[Subscription]) -> str:
    if not subs:
        return (
            "📋 У тебя пока нет подписок.\n\n"
            "Нажми <b>➕ Добавить подписку</b>, чтобы добавить первую."
        )

    lines = ["📋 <b>Твои подписки:</b>\n"]
    monthly_total = Decimal("0")

    for sub in subs:
        period_sym = "мес" if sub.period == "monthly" else "год"
        price_str = fmt_price(sub.price)
        rel = relative_days(sub.next_payment)
        short = short_date(sub.next_payment)
        lines.append(
            f"🔹 <b>{sub.name}</b> — {price_str} ₽/{period_sym}\n"
            f"   📅 {short} ({rel})"
        )
        if sub.period == "monthly":
            monthly_total += sub.price
        else:
            monthly_total += sub.price / 12

    lines.append("\n━━━━━━━━━━━━━━━")
    lines.append(f"💰 Итого в месяц: ~{fmt_price(monthly_total.quantize(Decimal('0.01')))} ₽")

    nearest = subs[0]
    rel_nearest = relative_days(nearest.next_payment)
    lines.append(f"📅 Ближайшее: <b>{nearest.name}</b> {rel_nearest}")

    return "\n".join(lines)


def _build_detail_text(sub: Subscription, cat_name: str | None) -> str:
    price_str = fmt_price(sub.price)
    period_label = PERIOD_LABELS.get(sub.period, sub.period)
    cat_display = cat_name if cat_name else "—"
    added = full_date(sub.created_at.date()) if hasattr(sub.created_at, "date") else full_date(sub.created_at)
    return (
        f"✏️ <b>{sub.name}</b>\n\n"
        f"💰 Цена: {price_str} ₽\n"
        f"🔁 Период: {period_label}\n"
        f"📅 Следующее списание: {full_date(sub.next_payment)}\n"
        f"🗂 Категория: {cat_display}\n"
        f"📆 Добавлена: {added}"
    )


# ──────────────────────────────────────────────────────────────────────────────
# "My subscriptions" list
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "my_subs")
async def show_subscriptions(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    subs = await _get_user_subs(session, callback.from_user.id)
    text = _build_list_text(subs)
    markup = subs_list_keyboard(subs)
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    await callback.answer()


# ──────────────────────────────────────────────────────────────────────────────
# Subscription detail
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("sub_detail:"))
async def show_sub_detail(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    sub_id = int(callback.data.split(":")[1])
    sub = await session.get(Subscription, sub_id)
    if not sub or sub.user_id != callback.from_user.id:
        await callback.answer("Подписка не найдена.", show_alert=True)
        return

    cats = await _get_user_categories(session, callback.from_user.id)
    cat_name = cats.get(sub.category_id) if sub.category_id else None
    text = _build_detail_text(sub, cat_name)
    await callback.message.edit_text(
        text,
        reply_markup=sub_detail_keyboard(sub.id),
        parse_mode="HTML",
    )
    await callback.answer()


# ──────────────────────────────────────────────────────────────────────────────
# Edit: NAME
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("edit_sub_name:"))
async def edit_name_ask(callback: CallbackQuery, state: FSMContext) -> None:
    sub_id = int(callback.data.split(":")[1])
    await state.update_data(sub_id=sub_id)
    await state.set_state(EditSubscription.name)
    await callback.message.edit_text(
        "✏️ Введи новое название подписки:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Отмена", callback_data=f"sub_detail:{sub_id}")]]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(StateFilter(EditSubscription.name))
async def edit_name_save(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    sub_id = data["sub_id"]
    new_name = message.text.strip()
    if not new_name:
        await message.answer("Название не может быть пустым. Попробуй ещё раз:")
        return

    sub = await session.get(Subscription, sub_id)
    if not sub or sub.user_id != message.from_user.id:
        await state.clear()
        await message.answer("Подписка не найдена.")
        return

    sub.name = new_name
    await session.commit()
    await state.clear()

    cats = await _get_user_categories(session, message.from_user.id)
    cat_name = cats.get(sub.category_id) if sub.category_id else None
    await message.answer(
        _build_detail_text(sub, cat_name),
        reply_markup=sub_detail_keyboard(sub.id),
        parse_mode="HTML",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Edit: PRICE
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("edit_sub_price:"))
async def edit_price_ask(callback: CallbackQuery, state: FSMContext) -> None:
    sub_id = int(callback.data.split(":")[1])
    await state.update_data(sub_id=sub_id)
    await state.set_state(EditSubscription.price)
    await callback.message.edit_text(
        "💰 Введи новую цену (например: <code>199</code> или <code>1505.50</code>):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Отмена", callback_data=f"sub_detail:{sub_id}")]]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(StateFilter(EditSubscription.price))
async def edit_price_save(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    sub_id = data["sub_id"]

    raw = message.text.strip().replace(",", ".")
    try:
        new_price = Decimal(raw)
        if new_price <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("Некорректная цена. Введи положительное число, например <code>199</code>:", parse_mode="HTML")
        return

    sub = await session.get(Subscription, sub_id)
    if not sub or sub.user_id != message.from_user.id:
        await state.clear()
        await message.answer("Подписка не найдена.")
        return

    sub.price = new_price
    await session.commit()
    await state.clear()

    cats = await _get_user_categories(session, message.from_user.id)
    cat_name = cats.get(sub.category_id) if sub.category_id else None
    await message.answer(
        _build_detail_text(sub, cat_name),
        reply_markup=sub_detail_keyboard(sub.id),
        parse_mode="HTML",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Edit: PERIOD
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("edit_sub_period:"))
async def edit_period_ask(callback: CallbackQuery, state: FSMContext) -> None:
    sub_id = int(callback.data.split(":")[1])
    await state.update_data(sub_id=sub_id)
    await state.set_state(EditSubscription.period)
    await callback.message.edit_text(
        "🔁 Выбери новый период:",
        reply_markup=period_keyboard(sub_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_period:"), StateFilter(EditSubscription.period))
async def edit_period_save(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    _, new_period, sub_id_str = callback.data.split(":")
    sub_id = int(sub_id_str)

    sub = await session.get(Subscription, sub_id)
    if not sub or sub.user_id != callback.from_user.id:
        await state.clear()
        await callback.answer("Подписка не найдена.", show_alert=True)
        return

    sub.period = new_period
    await session.commit()
    await state.clear()

    cats = await _get_user_categories(session, callback.from_user.id)
    cat_name = cats.get(sub.category_id) if sub.category_id else None
    await callback.message.edit_text(
        _build_detail_text(sub, cat_name),
        reply_markup=sub_detail_keyboard(sub.id),
        parse_mode="HTML",
    )
    await callback.answer()


# ──────────────────────────────────────────────────────────────────────────────
# Edit: NEXT PAYMENT DATE
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("edit_sub_date:"))
async def edit_date_ask(callback: CallbackQuery, state: FSMContext) -> None:
    sub_id = int(callback.data.split(":")[1])
    await state.update_data(sub_id=sub_id)
    await state.set_state(EditSubscription.next_payment)
    await callback.message.edit_text(
        "📅 Введи новую дату следующего списания в формате <code>ДД.ММ.ГГГГ</code>\n"
        "Например: <code>24.03.2026</code>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Отмена", callback_data=f"sub_detail:{sub_id}")]]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(StateFilter(EditSubscription.next_payment))
async def edit_date_save(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    sub_id = data["sub_id"]

    raw = message.text.strip()
    try:
        new_date = datetime.strptime(raw, "%d.%m.%Y").date()
    except ValueError:
        await message.answer(
            "Неверный формат. Введи дату в виде <code>ДД.ММ.ГГГГ</code>, например <code>24.03.2026</code>:",
            parse_mode="HTML",
        )
        return

    sub = await session.get(Subscription, sub_id)
    if not sub or sub.user_id != message.from_user.id:
        await state.clear()
        await message.answer("Подписка не найдена.")
        return

    sub.next_payment = new_date
    await session.commit()
    await state.clear()

    cats = await _get_user_categories(session, message.from_user.id)
    cat_name = cats.get(sub.category_id) if sub.category_id else None
    await message.answer(
        _build_detail_text(sub, cat_name),
        reply_markup=sub_detail_keyboard(sub.id),
        parse_mode="HTML",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Edit: CATEGORY
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("edit_sub_cat:"))
async def edit_cat_ask(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    sub_id = int(callback.data.split(":")[1])
    await state.update_data(sub_id=sub_id)
    await state.set_state(EditSubscription.category)

    cats = await _get_user_categories(session, callback.from_user.id)
    buttons: list[list[InlineKeyboardButton]] = []
    for cat_id, cat_name in cats.items():
        buttons.append(
            [InlineKeyboardButton(text=cat_name, callback_data=f"set_cat:{cat_id}:{sub_id}")]
        )
    # Option to clear category
    buttons.append(
        [InlineKeyboardButton(text="— Без категории", callback_data=f"set_cat:0:{sub_id}")]
    )
    buttons.append(
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data=f"sub_detail:{sub_id}")]
    )

    if not cats:
        text = (
            "🗂 У тебя пока нет категорий.\n"
            "Сначала создай категорию в разделе <b>Категории</b>."
        )
    else:
        text = "🗂 Выбери категорию:"

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("set_cat:"), StateFilter(EditSubscription.category))
async def edit_cat_save(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    parts = callback.data.split(":")
    cat_id_raw = int(parts[1])
    sub_id = int(parts[2])

    sub = await session.get(Subscription, sub_id)
    if not sub or sub.user_id != callback.from_user.id:
        await state.clear()
        await callback.answer("Подписка не найдена.", show_alert=True)
        return

    sub.category_id = None if cat_id_raw == 0 else cat_id_raw
    await session.commit()
    await state.clear()

    cats = await _get_user_categories(session, callback.from_user.id)
    cat_name = cats.get(sub.category_id) if sub.category_id else None
    await callback.message.edit_text(
        _build_detail_text(sub, cat_name),
        reply_markup=sub_detail_keyboard(sub.id),
        parse_mode="HTML",
    )
    await callback.answer()


# ──────────────────────────────────────────────────────────────────────────────
# Delete with confirmation
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("delete_sub_ask:"))
async def delete_sub_ask(callback: CallbackQuery, session: AsyncSession) -> None:
    sub_id = int(callback.data.split(":")[1])
    sub = await session.get(Subscription, sub_id)
    if not sub or sub.user_id != callback.from_user.id:
        await callback.answer("Подписка не найдена.", show_alert=True)
        return

    await callback.message.edit_text(
        f"🗑 Удалить подписку <b>{sub.name}</b>?\n\nЭто действие нельзя отменить.",
        reply_markup=delete_confirm_keyboard(sub_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_sub_confirm:"))
async def delete_sub_confirm(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    sub_id = int(callback.data.split(":")[1])
    sub = await session.get(Subscription, sub_id)
    if not sub or sub.user_id != callback.from_user.id:
        await callback.answer("Подписка не найдена.", show_alert=True)
        return

    name = sub.name
    await session.delete(sub)
    await session.commit()
    await state.clear()

    # Return to the subscription list
    subs = await _get_user_subs(session, callback.from_user.id)
    text = _build_list_text(subs)
    await callback.message.edit_text(
        f"✅ Подписка <b>{name}</b> удалена.\n\n{text}",
        reply_markup=subs_list_keyboard(subs),
        parse_mode="HTML",
    )
    await callback.answer()


# ──────────────────────────────────────────────────────────────────────────────
# ADD SUBSCRIPTION flow (preserved from original, triggered by add_sub callback)
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "add_sub")
async def add_sub_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AddSubscription.name)
    await callback.message.edit_text(
        "➕ <b>Новая подписка</b>\n\nВведи название подписки:\n<i>(например: Netflix, Spotify, Figma)</i>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Отмена", callback_data="back_to_main")]]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(StateFilter(AddSubscription.name))
async def add_sub_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("Название не может быть пустым. Введи название подписки:")
        return
    await state.update_data(name=name)
    await state.set_state(AddSubscription.price)
    await message.answer(
        f"💰 Цена <b>{name}</b>\n\nВведи сумму (например: <code>199</code> или <code>1505.50</code>):",
        parse_mode="HTML",
    )


@router.message(StateFilter(AddSubscription.price))
async def add_sub_price(message: Message, state: FSMContext) -> None:
    raw = message.text.strip().replace(",", ".")
    try:
        price = Decimal(raw)
        if price <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("Некорректная цена. Введи положительное число, например <code>199</code>:", parse_mode="HTML")
        return
    await state.update_data(price=str(price))
    await state.set_state(AddSubscription.period)
    await message.answer(
        "🔁 Выбери период подписки:",
        reply_markup=add_period_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("set_add_period:"), StateFilter(AddSubscription.period))
async def add_sub_period(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    period = callback.data.split(":")[1]
    await state.update_data(period=period)
    await state.set_state(AddSubscription.category)

    cats = await _get_user_categories(session, callback.from_user.id)
    buttons: list[list[InlineKeyboardButton]] = []
    for cat_id, cat_name in cats.items():
        buttons.append(
            [InlineKeyboardButton(text=cat_name, callback_data=f"add_cat:{cat_id}")]
        )
    buttons.append([InlineKeyboardButton(text="— Без категории", callback_data="add_cat:0")])

    await callback.message.edit_text(
        "🗂 Выбери категорию (или пропусти):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("add_cat:"), StateFilter(AddSubscription.category))
async def add_sub_category(callback: CallbackQuery, state: FSMContext) -> None:
    cat_id_raw = int(callback.data.split(":")[1])
    await state.update_data(category_id=None if cat_id_raw == 0 else cat_id_raw)
    await state.set_state(AddSubscription.next_payment)
    await callback.message.edit_text(
        "📅 Введи дату следующего списания в формате <code>ДД.ММ.ГГГГ</code>\n"
        "Например: <code>24.03.2026</code>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(StateFilter(AddSubscription.next_payment))
async def add_sub_next_payment(message: Message, state: FSMContext, session: AsyncSession) -> None:
    raw = message.text.strip()
    try:
        next_payment = datetime.strptime(raw, "%d.%m.%Y").date()
    except ValueError:
        await message.answer(
            "Неверный формат. Введи дату в виде <code>ДД.ММ.ГГГГ</code>, например <code>24.03.2026</code>:",
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    sub = Subscription(
        user_id=message.from_user.id,
        name=data["name"],
        price=Decimal(data["price"]),
        period=data["period"],
        category_id=data.get("category_id"),
        next_payment=next_payment,
    )
    session.add(sub)
    await session.commit()
    await state.clear()

    period_label = PERIOD_LABELS.get(sub.period, sub.period)
    await message.answer(
        f"✅ Подписка <b>{sub.name}</b> добавлена!\n\n"
        f"💰 {fmt_price(sub.price)} ₽ — {period_label}\n"
        f"📅 Следующее списание: {full_date(next_payment)}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📋 Мои подписки", callback_data="my_subs")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="back_to_main")],
            ]
        ),
        parse_mode="HTML",
    )
