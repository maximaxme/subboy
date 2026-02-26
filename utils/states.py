from aiogram.fsm.state import StatesGroup, State

class AddSubscription(StatesGroup):
    name = State()
    price = State()
    period = State()
    category = State()
    next_payment = State()

class ManageCategories(StatesGroup):
    name = State()
