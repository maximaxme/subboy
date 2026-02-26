from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date

from utils.states import AddSubscription
from database.models import Subscription, Category
from sqlalchemy import select

router = Router()

@router.callback_query(F.data == "add_sub")
async def start_add_subscription(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddSubscription.name)
    await callback.message.answer("➕ Новая подписка\nКак называется сервис?")
    await callback.answer()

@router.message(AddSubscription.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddSubscription.price)
    await message.answer("💰 Сколько списывают?")

@router.message(AddSubscription.price)
async def process_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text.replace(",", "."))
        await state.update_data(price=price)
        
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="📆 Раз в месяц", callback_data="period_monthly"))
        kb.row(types.InlineKeyboardButton(text="📆 Раз в год", callback_data="period_yearly"))
        
        await state.set_state(AddSubscription.period)
        await message.answer("🔁 Как часто?", reply_markup=kb.as_markup())
    except ValueError:
        await message.answer("Пожалуйста, введите число (например, 499 или 12.50)")

@router.callback_query(AddSubscription.period, F.data.startswith("period_"))
async def process_period(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    period = callback.data.split("_")[1]
    await state.update_data(period=period)
    
    # Получаем категории пользователя
    stmt = select(Category).where(Category.user_id == callback.from_user.id)
    result = await session.execute(stmt)
    categories = result.scalars().all()
    
    kb = InlineKeyboardBuilder()
    for cat in categories:
        kb.row(types.InlineKeyboardButton(text=cat.name, callback_data=f"cat_{cat.id}"))
    
    kb.row(types.InlineKeyboardButton(text="Без категории", callback_data="cat_none"))
    kb.row(types.InlineKeyboardButton(text="➕ Создать категорию", callback_data="cat_new"))
    
    await state.set_state(AddSubscription.category)
    await callback.message.edit_text("🗂 Выберите категорию:", reply_markup=kb.as_markup())
    await callback.answer()

@router.callback_query(AddSubscription.category, F.data.startswith("cat_"))
async def process_category(callback: types.CallbackQuery, state: FSMContext):
    cat_id = callback.data.split("_")[1]
    if cat_id == "none":
        await state.update_data(category_id=None)
    elif cat_id == "new":
        # В идеале здесь должен быть переход к созданию категории, 
        # но для упрощения пока пропустим или сделаем позже
        await state.update_data(category_id=None)
    else:
        await state.update_data(category_id=int(cat_id))
    
    # Теперь дата следующего списания
    # Для простоты предложим сегодня и выбор даты
    kb = InlineKeyboardBuilder()
    today = date.today()
    kb.row(types.InlineKeyboardButton(text=f"Сегодня ({today.strftime('%d.%m')})", callback_data=f"date_{today.isoformat()}"))
    
    # Можно добавить еще вариантов или просто попросить ввести дату
    await state.set_state(AddSubscription.next_payment)
    await callback.message.edit_text("📅 Когда следующее списание? (Введите в формате ДД.ММ.ГГГГ или выберите сегодня)", reply_markup=kb.as_markup())
    await callback.answer()

@router.callback_query(AddSubscription.next_payment, F.data.startswith("date_"))
async def process_date_callback(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    dt_str = callback.data.split("_")[1]
    next_payment = date.fromisoformat(dt_str)
    await save_subscription(callback.message, state, session, next_payment)
    await callback.answer()

@router.message(AddSubscription.next_payment)
async def process_date_message(message: types.Message, state: FSMContext, session: AsyncSession):
    try:
        next_payment = datetime.strptime(message.text, "%d.%m.%Y").date()
        await save_subscription(message, state, session, next_payment)
    except ValueError:
        await message.answer("Пожалуйста, введите дату в формате ДД.ММ.ГГГГ (например, 24.01.2026)")

async def save_subscription(message: types.Message, state: FSMContext, session: AsyncSession, next_payment: date):
    data = await state.get_data()
    
    new_sub = Subscription(
        user_id=message.chat.id,
        name=data['name'],
        price=data['price'],
        period=data['period'],
        category_id=data.get('category_id'),
        next_payment=next_payment
    )
    
    session.add(new_sub)
    await session.commit()
    
    await state.clear()
    await message.answer("✅ Готово! Я всё сохранил 👍")

@router.callback_query(F.data == "my_subs")
async def show_subscriptions(callback: types.CallbackQuery, session: AsyncSession):
    stmt = select(Subscription).where(Subscription.user_id == callback.from_user.id)
    result = await session.execute(stmt)
    subscriptions = result.scalars().all()
    
    if not subscriptions:
        await callback.message.answer("У вас пока нет подписок. Нажмите ➕ Добавить подписку, чтобы создать первую!")
        await callback.answer()
        return

    text = "📋 Ваши подписки:\n\n"
    kb = InlineKeyboardBuilder()
    
    for sub in subscriptions:
        period_text = "в месяц" if sub.period == "monthly" else "в год"
        text += f"• {sub.name}: {sub.price} ₽ {period_text}\n"
        kb.row(types.InlineKeyboardButton(text=f"✏️ {sub.name}", callback_data=f"edit_sub_{sub.id}"))
    
    await callback.message.answer(text, reply_markup=kb.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("edit_sub_"))
async def edit_subscription_menu(callback: types.CallbackQuery, session: AsyncSession):
    sub_id = int(callback.data.split("_")[2])
    stmt = select(Subscription).where(Subscription.id == sub_id)
    result = await session.execute(stmt)
    sub = result.scalar_one_or_none()
    
    if not sub:
        await callback.answer("Подписка не найдена")
        return
        
    text = (
        f"✏️ Редактирование: {sub.name}\n"
        f"💰 Сумма: {sub.price} ₽\n"
        f"🔁 Период: {'Раз в месяц' if sub.period == 'monthly' else 'Раз в год'}\n"
        f"📅 Следующее списание: {sub.next_payment.strftime('%d.%m.%Y')}"
    )
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_sub_{sub.id}"))
    kb.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="my_subs"))
    
    await callback.message.edit_text(text, reply_markup=kb.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("del_sub_"))
async def delete_subscription(callback: types.CallbackQuery, session: AsyncSession):
    sub_id = int(callback.data.split("_")[2])
    stmt = select(Subscription).where(Subscription.id == sub_id)
    result = await session.execute(stmt)
    sub = result.scalar_one_or_none()
    
    if sub:
        await session.delete(sub)
        await session.commit()
        await callback.answer("Подписка удалена")
        await show_subscriptions(callback, session)
    else:
        await callback.answer("Подписка не найдена")
    # Здесь можно было бы вернуть в главное меню
