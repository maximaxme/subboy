from aiogram.fsm.state import State, StatesGroup


class AddSubscription(StatesGroup):
    """States for adding a new subscription step by step."""
    name = State()
    price = State()
    period = State()
    category = State()
    next_payment = State()


class EditSubscription(StatesGroup):
    """States for editing an existing subscription field by field."""
    # Which subscription is being edited is stored in FSM data as 'sub_id'
    name = State()
    price = State()
    period = State()
    next_payment = State()
    category = State()


class ManageCategories(StatesGroup):
    """States for creating / renaming categories."""
    name = State()
