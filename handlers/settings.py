"""
handlers/settings.py — Notification settings management.

Allows users to toggle:
- day_before: reminder the day before a payment
- weekly: Monday digest of upcoming payments
- monthly: monthly expense summary
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import NotificationSettings

router = Router()


def _check(enabled: bool) -> str:
    return "✅" if enabled else "☑️"


def settings_keyboard(ns: NotificationSettings) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{_check(ns.day_before)} За день до списания",
                    callback_data="toggle_day_before",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{_check(ns.weekly)} Еженедельный дайджест (Пн)",
                    callback_data="toggle_weekly",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{_check(ns.monthly)} Ежемесячный отчёт",
                    callback_data="toggle_monthly",
                )
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")],
        ]
    )


async def _get_or_create_settings(session: AsyncSession, user_id: int) -> NotificationSettings:
    ns = await session.get(NotificationSettings, user_id)
    if ns is None:
        ns = NotificationSettings(
            user_id=user_id,
            day_before=True,
            weekly=False,
            monthly=False,
        )
        session.add(ns)
        await session.commit()
    return ns


@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery, session: AsyncSession) -> None:
    ns = await _get_or_create_settings(session, callback.from_user.id)
    await callback.message.edit_text(
        "⚙️ <b>Настройки уведомлений</b>\n\n"
        "Выбери, какие уведомления ты хочешь получать:",
        reply_markup=settings_keyboard(ns),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "toggle_day_before")
async def toggle_day_before(callback: CallbackQuery, session: AsyncSession) -> None:
    ns = await _get_or_create_settings(session, callback.from_user.id)
    ns.day_before = not ns.day_before
    await session.commit()
    await callback.message.edit_reply_markup(reply_markup=settings_keyboard(ns))
    status = "включены" if ns.day_before else "отключены"
    await callback.answer(f"Напоминания за день {status}.")


@router.callback_query(F.data == "toggle_weekly")
async def toggle_weekly(callback: CallbackQuery, session: AsyncSession) -> None:
    ns = await _get_or_create_settings(session, callback.from_user.id)
    ns.weekly = not ns.weekly
    await session.commit()
    await callback.message.edit_reply_markup(reply_markup=settings_keyboard(ns))
    status = "включён" if ns.weekly else "отключён"
    await callback.answer(f"Еженедельный дайджест {status}.")


@router.callback_query(F.data == "toggle_monthly")
async def toggle_monthly(callback: CallbackQuery, session: AsyncSession) -> None:
    ns = await _get_or_create_settings(session, callback.from_user.id)
    ns.monthly = not ns.monthly
    await session.commit()
    await callback.message.edit_reply_markup(reply_markup=settings_keyboard(ns))
    status = "включён" if ns.monthly else "отключён"
    await callback.answer(f"Ежемесячный отчёт {status}.")
