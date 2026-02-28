"""
handlers/subscriptions.py — Complete rewrite.

Features:
- List subscriptions (paginated, per-category filter)
- Add subscription (multi-step FSM)
- Edit subscription (multi-step FSM, inline button)
- Delete subscription (confirm dialog, inline button)
- Toggle active/paused (inline button)
"""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Optional

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

from database.models import Subscription, Category
from utils.states import AddSubStates, EditSubStates

logger = logging.getLogger(__name__)
router = Router(name="subscriptions")

# ─── Constants ────────────────────────────────────────────────────────────────

PAGE_SIZE = 5

BILLING_CYCLES = [
    ("Monthly", "monthly"),
    ("Yearly", "yearly"),
    ("Weekly", "weekly"),
    ("Daily", "daily"),
]

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _sub_card(sub: Subscription) -> str:
    """Render a single subscription as an HTML card."""
    status = "✅ Active" if sub.is_active else "⏸ Paused"
    return (
        f"<b>{sub.name}</b>\n"
        f"  💰 {sub.amount:.2f} {sub.currency} / {sub.billing_cycle}\n"
        f"  📅 Next: {sub.next_billing_date}\n"
        f"  🏷 Category: {sub.category.name if sub.category else '—'}\n"
        f"  {status}\n"
    )


def _sub_list_keyboard(
    subscriptions: list[Subscription],
    page: int,
    total_pages: int,
    category_id: Optional[int] = None,
) -> InlineKeyboardMarkup:
    """Build paginated inline keyboard for subscription list."""
    rows: list[list[InlineKeyboardButton]] = []

    for sub in subscriptions:
        toggle_label = "⏸ Pause" if sub.is_active else "▶️ Resume"
        rows.append([
            InlineKeyboardButton(
                text=f"{sub.name} — {sub.amount:.2f} {sub.currency}",
                callback_data=f"sub:view:{sub.id}",
            )
        ])
        rows.append([
            InlineKeyboardButton(text="✏️ Edit",   callback_data=f"sub:edit:{sub.id}"),
            InlineKeyboardButton(text=toggle_label, callback_data=f"sub:toggle:{sub.id}"),
            InlineKeyboardButton(text="🗑 Delete",  callback_data=f"sub:delete:{sub.id}"),
        ])

    # Pagination row
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        cat_part = f":{category_id}" if category_id else ":0"
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"sub:page:{page - 1}{cat_part}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page + 1 < total_pages:
        cat_part = f":{category_id}" if category_id else ":0"
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"sub:page:{page + 1}{cat_part}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="➕ Add Subscription", callback_data="sub:add")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _billing_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"billing:{value}")]
            for label, value in BILLING_CYCLES
        ]
    )


async def _get_category_keyboard(session: AsyncSession, user_id: int) -> InlineKeyboardMarkup:
    result = await session.execute(
        select(Category).where(Category.user_id == user_id).order_by(Category.name)
    )
    categories = result.scalars().all()
    rows = [
        [InlineKeyboardButton(text=cat.name, callback_data=f"cat_pick:{cat.id}")]
        for cat in categories
    ]
    rows.append([InlineKeyboardButton(text="— No category —", callback_data="cat_pick:0")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _fetch_page(
    session: AsyncSession,
    user_id: int,
    page: int,
    category_id: Optional[int] = None,
) -> tuple[list[Subscription], int]:
    """Return (subscriptions_on_page, total_pages)."""
    q = select(Subscription).where(Subscription.user_id == user_id)
    if category_id:
        q = q.where(Subscription.category_id == category_id)
    q = q.order_by(Subscription.next_billing_date)

    result = await session.execute(q)
    all_subs = result.scalars().all()
    total_pages = max(1, (len(all_subs) + PAGE_SIZE - 1) // PAGE_SIZE)
    start = page * PAGE_SIZE
    return list(all_subs[start: start + PAGE_SIZE]), total_pages


# ─── List / Entry ──────────────────────────────────────────────────────────────


@router.message(Command("subscriptions"))
@router.message(F.text == "📋 My Subscriptions")
async def cmd_subscriptions(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    user_id = message.from_user.id
    subs, total_pages = await _fetch_page(session, user_id, 0)
    if not subs:
        await message.answer(
            "You have no subscriptions yet.\n\nTap <b>➕ Add Subscription</b> to get started.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Add Subscription", callback_data="sub:add")]
                ]
            ),
        )
        return
    text = "<b>Your Subscriptions</b>\n\n" + "\n".join(_sub_card(s) for s in subs)
    await message.answer(
        text,
        reply_markup=_sub_list_keyboard(subs, 0, total_pages),
    )


@router.callback_query(F.data.startswith("sub:page:"))
async def cb_page(callback: CallbackQuery, session: AsyncSession) -> None:
    _, _, rest = callback.data.split(":", 2)
    parts = rest.split(":")
    page = int(parts[0])
    category_id = int(parts[1]) if len(parts) > 1 and parts[1] != "0" else None
    user_id = callback.from_user.id

    subs, total_pages = await _fetch_page(session, user_id, page, category_id)
    text = "<b>Your Subscriptions</b>\n\n" + "\n".join(_sub_card(s) for s in subs)
    await callback.message.edit_text(
        text,
        reply_markup=_sub_list_keyboard(subs, page, total_pages, category_id),
    )
    await callback.answer()


# ─── View (detail) ─────────────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("sub:view:"))
async def cb_view(callback: CallbackQuery, session: AsyncSession) -> None:
    sub_id = int(callback.data.split(":")[2])
    sub = await session.get(Subscription, sub_id)
    if not sub or sub.user_id != callback.from_user.id:
        await callback.answer("Not found.", show_alert=True)
        return
    await callback.answer(_sub_card(sub), show_alert=True)


# ─── Toggle active ─────────────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("sub:toggle:"))
async def cb_toggle(callback: CallbackQuery, session: AsyncSession) -> None:
    sub_id = int(callback.data.split(":")[2])
    sub = await session.get(Subscription, sub_id)
    if not sub or sub.user_id != callback.from_user.id:
        await callback.answer("Not found.", show_alert=True)
        return
    sub.is_active = not sub.is_active
    await session.commit()
    status = "resumed ▶️" if sub.is_active else "paused ⏸"
    await callback.answer(f"{sub.name} {status}")
    # Refresh list
    subs, total_pages = await _fetch_page(session, callback.from_user.id, 0)
    text = "<b>Your Subscriptions</b>\n\n" + "\n".join(_sub_card(s) for s in subs)
    await callback.message.edit_text(
        text,
        reply_markup=_sub_list_keyboard(subs, 0, total_pages),
    )


# ─── Delete ────────────────────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("sub:delete:"))
async def cb_delete_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    sub_id = int(callback.data.split(":")[2])
    sub = await session.get(Subscription, sub_id)
    if not sub or sub.user_id != callback.from_user.id:
        await callback.answer("Not found.", show_alert=True)
        return
    await callback.message.answer(
        f"Are you sure you want to delete <b>{sub.name}</b>?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Yes, delete", callback_data=f"sub:del_confirm:{sub_id}"),
                    InlineKeyboardButton(text="❌ Cancel",      callback_data="sub:del_cancel"),
                ]
            ]
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sub:del_confirm:"))
async def cb_delete_execute(callback: CallbackQuery, session: AsyncSession) -> None:
    sub_id = int(callback.data.split(":")[2])
    sub = await session.get(Subscription, sub_id)
    if sub and sub.user_id == callback.from_user.id:
        await session.delete(sub)
        await session.commit()
        await callback.message.edit_text(f"🗑 <b>{sub.name}</b> deleted.")
    else:
        await callback.answer("Not found.", show_alert=True)
    await callback.answer()


@router.callback_query(F.data == "sub:del_cancel")
async def cb_delete_cancel(callback: CallbackQuery) -> None:
    await callback.message.edit_text("Deletion cancelled.")
    await callback.answer()


# ─── Add subscription FSM ──────────────────────────────────────────────────────


@router.callback_query(F.data == "sub:add")
async def cb_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddSubStates.waiting_name)
    await callback.message.answer("Enter subscription name (e.g. <i>Netflix</i>):")
    await callback.answer()


@router.message(AddSubStates.waiting_name)
async def add_sub_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(AddSubStates.waiting_amount)
    await message.answer("Enter the amount (e.g. <i>9.99</i>):")


@router.message(AddSubStates.waiting_amount)
async def add_sub_amount(message: Message, state: FSMContext) -> None:
    try:
        amount = Decimal(message.text.strip().replace(",", "."))
    except InvalidOperation:
        await message.answer("⚠️ Invalid amount. Please enter a number like <i>9.99</i>:")
        return
    await state.update_data(amount=str(amount))
    await state.set_state(AddSubStates.waiting_currency)
    await message.answer("Enter currency (e.g. <i>USD</i>, <i>EUR</i>, <i>RUB</i>):")


@router.message(AddSubStates.waiting_currency)
async def add_sub_currency(message: Message, state: FSMContext) -> None:
    await state.update_data(currency=message.text.strip().upper())
    await state.set_state(AddSubStates.waiting_billing_cycle)
    await message.answer("Choose billing cycle:", reply_markup=_billing_keyboard())


@router.callback_query(F.data.startswith("billing:"), AddSubStates.waiting_billing_cycle)
async def add_sub_billing(callback: CallbackQuery, state: FSMContext) -> None:
    cycle = callback.data.split(":")[1]
    await state.update_data(billing_cycle=cycle)
    await state.set_state(AddSubStates.waiting_next_date)
    await callback.message.answer(
        "Enter next billing date (YYYY-MM-DD), or type <i>today</i>:"
    )
    await callback.answer()


@router.message(AddSubStates.waiting_next_date)
async def add_sub_date(message: Message, state: FSMContext, session: AsyncSession) -> None:
    from datetime import date, timedelta
    text = message.text.strip().lower()
    if text == "today":
        next_date = date.today()
    else:
        try:
            next_date = date.fromisoformat(text)
        except ValueError:
            await message.answer("⚠️ Invalid date. Use YYYY-MM-DD or type <i>today</i>:")
            return
    await state.update_data(next_billing_date=str(next_date))
    await state.set_state(AddSubStates.waiting_category)
    await message.answer(
        "Choose a category (optional):",
        reply_markup=await _get_category_keyboard(session, message.from_user.id),
    )


@router.callback_query(F.data.startswith("cat_pick:"), AddSubStates.waiting_category)
async def add_sub_category(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    from datetime import date
    cat_id_raw = callback.data.split(":")[1]
    category_id = int(cat_id_raw) if cat_id_raw != "0" else None

    data = await state.get_data()
    sub = Subscription(
        user_id=callback.from_user.id,
        name=data["name"],
        amount=Decimal(data["amount"]),
        currency=data["currency"],
        billing_cycle=data["billing_cycle"],
        next_billing_date=date.fromisoformat(data["next_billing_date"]),
        category_id=category_id,
        is_active=True,
    )
    session.add(sub)
    await session.commit()
    await state.clear()
    await callback.message.answer(
        f"✅ Subscription <b>{sub.name}</b> added!"
    )
    await callback.answer()


# ─── Edit subscription FSM ─────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("sub:edit:"))
async def cb_edit_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    sub_id = int(callback.data.split(":")[2])
    sub = await session.get(Subscription, sub_id)
    if not sub or sub.user_id != callback.from_user.id:
        await callback.answer("Not found.", show_alert=True)
        return

    await state.set_state(EditSubStates.choosing_field)
    await state.update_data(sub_id=sub_id)

    await callback.message.answer(
        f"Editing <b>{sub.name}</b>. What would you like to change?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Name",          callback_data="edit_field:name")],
                [InlineKeyboardButton(text="Amount",        callback_data="edit_field:amount")],
                [InlineKeyboardButton(text="Currency",      callback_data="edit_field:currency")],
                [InlineKeyboardButton(text="Billing cycle", callback_data="edit_field:billing_cycle")],
                [InlineKeyboardButton(text="Next date",     callback_data="edit_field:next_date")],
                [InlineKeyboardButton(text="Category",      callback_data="edit_field:category")],
                [InlineKeyboardButton(text="❌ Cancel",      callback_data="edit_field:cancel")],
            ]
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_field:"), EditSubStates.choosing_field)
async def cb_edit_field(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    field = callback.data.split(":")[1]
    if field == "cancel":
        await state.clear()
        await callback.message.edit_text("Edit cancelled.")
        await callback.answer()
        return

    await state.update_data(field=field)

    if field == "billing_cycle":
        await state.set_state(EditSubStates.waiting_new_value)
        await callback.message.answer("Choose new billing cycle:", reply_markup=_billing_keyboard())
    elif field == "category":
        await state.set_state(EditSubStates.waiting_new_value)
        user_id = callback.from_user.id
        await callback.message.answer(
            "Choose new category:",
            reply_markup=await _get_category_keyboard(session, user_id),
        )
    else:
        prompts = {
            "name":     "Enter new name:",
            "amount":   "Enter new amount (e.g. 9.99):",
            "currency": "Enter new currency (e.g. USD):",
            "next_date": "Enter new next billing date (YYYY-MM-DD):",
        }
        await state.set_state(EditSubStates.waiting_new_value)
        await callback.message.answer(prompts.get(field, "Enter new value:"))
    await callback.answer()


@router.message(EditSubStates.waiting_new_value)
async def edit_sub_text_value(message: Message, state: FSMContext, session: AsyncSession) -> None:
    from datetime import date
    data = await state.get_data()
    sub_id = data["sub_id"]
    field  = data["field"]
    value  = message.text.strip()

    sub = await session.get(Subscription, sub_id)
    if not sub or sub.user_id != message.from_user.id:
        await message.answer("Subscription not found.")
        await state.clear()
        return

    if field == "name":
        sub.name = value
    elif field == "amount":
        try:
            sub.amount = Decimal(value.replace(",", "."))
        except InvalidOperation:
            await message.answer("⚠️ Invalid amount.")
            return
    elif field == "currency":
        sub.currency = value.upper()
    elif field == "next_date":
        try:
            sub.next_billing_date = date.fromisoformat(value)
        except ValueError:
            await message.answer("⚠️ Invalid date (use YYYY-MM-DD).")
            return

    await session.commit()
    await state.clear()
    await message.answer(f"✅ <b>{sub.name}</b> updated successfully!")


@router.callback_query(F.data.startswith("billing:"), EditSubStates.waiting_new_value)
async def edit_sub_billing(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    sub = await session.get(Subscription, data["sub_id"])
    if sub and sub.user_id == callback.from_user.id:
        sub.billing_cycle = callback.data.split(":")[1]
        await session.commit()
        await callback.message.answer(f"✅ <b>{sub.name}</b> billing cycle updated!")
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("cat_pick:"), EditSubStates.waiting_new_value)
async def edit_sub_category(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    sub = await session.get(Subscription, data["sub_id"])
    if sub and sub.user_id == callback.from_user.id:
        cat_id_raw = callback.data.split(":")[1]
        sub.category_id = int(cat_id_raw) if cat_id_raw != "0" else None
        await session.commit()
        await callback.message.answer(f"✅ <b>{sub.name}</b> category updated!")
    await state.clear()
    await callback.answer()
