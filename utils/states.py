from aiogram.fsm.state import State, StatesGroup


class AddSubStates(StatesGroup):
    waiting_name          = State()
    waiting_amount        = State()
    waiting_currency      = State()
    waiting_billing_cycle = State()
    waiting_next_date     = State()
    waiting_category      = State()


class EditSubStates(StatesGroup):
    choosing_field    = State()
    waiting_new_value = State()


class CategoryStates(StatesGroup):
    waiting_name   = State()
    waiting_rename = State()


class SettingsStates(StatesGroup):
    waiting_hour = State()
