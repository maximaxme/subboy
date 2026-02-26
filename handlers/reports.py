from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from datetime import datetime
from decimal import Decimal

from database.models import Subscription, Category

router = Router()

@router.callback_query(F.data == "reports")
async def show_reports_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    # Предложим текущий месяц и пару предыдущих
    now = datetime.now()
    months = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    
    for i in range(3):
        month_idx = (now.month - 1 - i) % 12
        year = now.year if now.month - i > 0 else now.year - 1
        month_name = months[month_idx]
        kb.row(types.InlineKeyboardButton(
            text=f"{month_name} {year}", 
            callback_data=f"report_{year}_{month_idx + 1}"
        ))
    
    kb.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main"))
    
    await callback.message.edit_text("📊 Отчёты\nЗа какой месяц показать расходы?", reply_markup=kb.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("report_"))
async def show_monthly_report(callback: types.CallbackQuery, session: AsyncSession):
    _, year, month = callback.data.split("_")
    year, month = int(year), int(month)
    
    # Получаем все подписки пользователя
    stmt = select(Subscription).options(joinedload(Subscription.category)).where(
        Subscription.user_id == callback.from_user.id
    )
    result = await session.execute(stmt)
    subscriptions = result.scalars().all()
    
    total = Decimal(0)
    by_category = {}
    
    for sub in subscriptions:
        # Если подписка годовая, берем 1/12
        monthly_price = sub.price if sub.period == "monthly" else sub.price / 12
        total += monthly_price
        
        cat_name = sub.category.name if sub.category else "Без категории"
        by_category[cat_name] = by_category.get(cat_name, Decimal(0)) + monthly_price
    
    months = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    month_name = months[month - 1]
    
    text = (
        f"📅 {month_name} {year}\n"
        f"💸 Всего: {total:.2f} ₽\n\n"
        f"🗂 По категориям:\n"
    )
    
    for cat, amount in by_category.items():
        text += f"• {cat} — {amount:.2f} ₽\n"
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="⬅️ Назад к отчетам", callback_data="reports"))
    
    await callback.message.edit_text(text, reply_markup=kb.as_markup())
    await callback.answer()
