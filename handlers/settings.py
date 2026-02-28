"""
handlers/settings.py — Notification settings management.

Features:
- View current notification settings
- Enable/disable notifications
- Set notification days before billing (1, 3, 7 days)
- Set notification time (hour)
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
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from utils.states import SettingsStates

logger = logging.getLogger(__name__)
router = Router(name="settings")


# ─── Keyboards ─────────────────────────────────────────────────────────────────


def _settings_keyboard(user: User) -> InlineKeyboardMarkup:
    notif_label = "🔕 Disable notifications" if user.notifications_enabled else "🔔 Enable notifications"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=notif_label,             callback_data="settings:toggle_notif")],
            [InlineKeyboardButton(text="📅 Days before billing", callback_data="settings:days")],
            [InlineKeyboardButton(text="🕐 Notification time",   callback_data="settings:time")],
        ]
    )


def _days_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 day before",  callback_data="settings:set_days:1")],
            [InlineKeyboardButton(text="3 days before", callback_data="settings:set_days:3")],
            [InlineKeyboardButton(text="7 days before", callback_data="settings:set_days:7")],
        ]
    )


# ─── Entry ─────────────────────────────────────────────────────────────────────


@router.message(Command("settings"))
@router.message(F.text == "⚙️ Settings")
async def cmd_settings(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    user = await session.get(User, message.from_user.id)
    if not user:
        await message.answer("Please start the bot first with /start.")
        return
    text = _settings_text(user)
    await message.answer(text, reply_markup=_settings_keyboard(user))


def _settings_text(user: User) -> str:
    status = "✅ Enabled" if user.notifications_enabled else "❌ Disabled"
    return (
        "<b>⚙️ Notification Settings</b>\n\n"
        f"  Status:        {status}\n"
        f"  Days before:   {user.notify_days_before} day(s)\n"
        f"  Notify at:     {user.notify_hour:02d}:00\n"
    )


# ─── Toggle ────────────────────────────────────────────────────────────────────


@router.callback_query(F.data == "settings:toggle_notif")
async def cb_toggle_notif(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await session.get(User, callback.from_user.id)
    if not user:
        await callback.answer("User not found.", show_alert=True)
        return
    user.notifications_enabled = not user.notifications_enabled
    await session.commit()
    await callback.message.edit_text(
        _settings_text(user),
        reply_markup=_settings_keyboard(user),
    )
    await callback.answer()


# ─── Days before ───────────────────────────────────────────────────────────────


@router.callback_query(F.data == "settings:days")
async def cb_days_menu(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "How many days before billing should I notify you?",
        reply_markup=_days_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:set_days:"))
async def cb_set_days(callback: CallbackQuery, session: AsyncSession) -> None:
    days = int(callback.data.split(":")[2])
    user = await session.get(User, callback.from_user.id)
    if user:
        user.notify_days_before = days
        await session.commit()
        await callback.message.edit_text(
            f"✅ I will notify you {days} day(s) before each billing.",
        )
    await callback.answer()


# ─── Notify hour ───────────────────────────────────────────────────────────────


@router.callback_query(F.data == "settings:time")
async def cb_time_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsStates.waiting_hour)
    await callback.message.answer(
        "Enter the hour for notifications (0–23), e.g. <i>9</i> for 9:00 AM:"
    )
    await callback.answer()


@router.message(SettingsStates.waiting_hour)
async def settings_set_hour(message: Message, state: FSMContext, session: AsyncSession) -> None:
    try:
        hour = int(message.text.strip())
        if not 0 <= hour <= 23:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Please enter a valid hour between 0 and 23.")
        return
    user = await session.get(User, message.from_user.id)
    if user:
        user.notify_hour = hour
        await session.commit()
        await message.answer(f"✅ Notification time set to {hour:02d}:00.")
    await state.clear()
