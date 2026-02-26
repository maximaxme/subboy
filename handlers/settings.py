from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import NotificationSettings

router = Router()

@router.callback_query(F.data == "settings")
async def show_settings(callback: types.CallbackQuery, session: AsyncSession):
    stmt = select(NotificationSettings).where(NotificationSettings.user_id == callback.from_user.id)
    result = await session.execute(stmt)
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = NotificationSettings(user_id=callback.from_user.id)
        session.add(settings)
        await session.commit()
    
    text = "🔔 Уведомления\nВыбери, что напоминать:"
    kb = InlineKeyboardBuilder()
    
    def get_mark(val: bool) -> str:
        return "✅" if val else "⬜"
    
    kb.row(types.InlineKeyboardButton(
        text=f"{get_mark(settings.day_before)} За день до списания", 
        callback_data="toggle_day_before"
    ))
    kb.row(types.InlineKeyboardButton(
        text=f"{get_mark(settings.weekly)} Платежи на этой неделе", 
        callback_data="toggle_weekly"
    ))
    kb.row(types.InlineKeyboardButton(
        text=f"{get_mark(settings.monthly)} Платежи в этом месяце", 
        callback_data="toggle_monthly"
    ))
    
    kb.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main"))
    
    await callback.message.edit_text(text, reply_markup=kb.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("toggle_"))
async def toggle_setting(callback: types.CallbackQuery, session: AsyncSession):
    setting_name = callback.data.replace("toggle_", "")
    stmt = select(NotificationSettings).where(NotificationSettings.user_id == callback.from_user.id)
    result = await session.execute(stmt)
    settings = result.scalar_one_or_none()
    
    if settings:
        current_val = getattr(settings, setting_name)
        setattr(settings, setting_name, not current_val)
        await session.commit()
        await show_settings(callback, session)
    else:
        await callback.answer("Настройки не найдены")
