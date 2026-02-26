from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from keyboards.main_menu import main_menu_keyboard

router = Router()

@router.message(Command("menu"))
async def show_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Чем займёмся?",
        reply_markup=main_menu_keyboard()
    )
