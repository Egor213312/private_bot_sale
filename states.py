from aiogram.fsm.state import State, StatesGroup

class RegistrationState(StatesGroup):
    """Состояния для процесса регистрации"""
    full_name = State()  # Полное имя пользователя
    email = State()      # Email пользователя
