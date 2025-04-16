from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from states import Registration
from models import User
from database import async_session
from sqlalchemy import select, delete

router = Router()

# Проверка email
def is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None

# Хэндлер /start
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    
    async with async_session() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            await message.answer(
                "🔄 Вы уже зарегистрированы!\n"
                "Используйте /info для просмотра профиля\n"
                "Или /buy для активации подписки"
            )
            return
            
    await message.answer("👋 Добро пожаловать в закрытый клуб!\nПожалуйста, введите ваше имя:")
    await state.set_state(Registration.full_name)

# Обработка имени
@router.message(Registration.full_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("📧 Теперь введите ваш email:")
    await state.set_state(Registration.email)

# Обработка email
@router.message(Registration.email)
async def process_email(message: Message, state: FSMContext):
    if not is_valid_email(message.text):
        await message.answer("❌ Неверный формат email. Попробуйте еще раз:")
        return
        
    data = await state.get_data()
    telegram_id = message.from_user.id
    
    async with async_session() as session:
        # Проверяем, не зарегистрирован ли пользователь снова
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            await message.answer("ℹ️ Вы уже зарегистрированы ранее!")
            await state.clear()
            return
            
        # Создаем нового пользователя
        user = User(
            telegram_id=telegram_id,
            full_name=data["full_name"],
            email=message.text
        )
        session.add(user)
        await session.commit()
    
    await message.answer(
        "✅ Регистрация завершена!\n"
        "Теперь вы можете:\n"
        "- Посмотреть профиль: /info\n"
        "- Активировать подписку: /buy"
    )
    await state.clear()