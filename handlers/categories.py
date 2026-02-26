from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import Category
from utils.states import ManageCategories

router = Router()

@router.callback_query(F.data == "categories")
async def show_categories(callback: types.CallbackQuery, session: AsyncSession):
    stmt = select(Category).where(Category.user_id == callback.from_user.id)
    result = await session.execute(stmt)
    categories = result.scalars().all()
    
    text = "🗂 Категории расходов\nНаведи порядок — так отчёты будут полезнее 😉"
    kb = InlineKeyboardBuilder()
    
    for cat in categories:
        kb.row(
            types.InlineKeyboardButton(text=cat.name, callback_data=f"cat_info_{cat.id}"),
            types.InlineKeyboardButton(text="🗑", callback_data=f"del_cat_{cat.id}")
        )
    
    kb.row(types.InlineKeyboardButton(text="➕ Новая категория", callback_data="add_cat"))
    kb.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main"))
    
    await callback.message.edit_text(text, reply_markup=kb.as_markup())
    await callback.answer()

@router.callback_query(F.data == "add_cat")
async def add_category_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ManageCategories.name)
    await callback.message.answer("Введите название новой категории:")
    await callback.answer()

@router.message(ManageCategories.name)
async def process_category_name(message: types.Message, state: FSMContext, session: AsyncSession):
    new_cat = Category(
        user_id=message.from_user.id,
        name=message.text
    )
    session.add(new_cat)
    await session.commit()
    
    await state.clear()
    await message.answer(f"✅ Категория '{message.text}' создана!")
    # Показать список категорий снова
    # В реальном боте лучше вызвать функцию отображения
    # Но для этого нужно передать callback или сымитировать его

@router.callback_query(F.data.startswith("del_cat_"))
async def delete_category(callback: types.CallbackQuery, session: AsyncSession):
    cat_id = int(callback.data.split("_")[2])
    stmt = select(Category).where(Category.id == cat_id)
    result = await session.execute(stmt)
    cat = result.scalar_one_or_none()
    
    if cat:
        await session.delete(cat)
        await session.commit()
        await callback.answer("Категория удалена")
        await show_categories(callback, session)
    else:
        await callback.answer("Категория не найдена")
