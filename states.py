from aiogram.fsm.state import StatesGroup, State

class Registration(StatesGroup):
    full_name = State()
    email = State()
