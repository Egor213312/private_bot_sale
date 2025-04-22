from aiogram import types, Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from db import get_user_by_telegram_id, create_user
from states import RegistrationState
from sqlalchemy.ext.asyncio import AsyncSession
from utils.subscription_manager import check_subscription_status
from handlers.invite import cmd_invite
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
import logging
import re

logger = logging.getLogger(__name__)
router = Router()

class UserRegistration(StatesGroup):
    waiting_for_phone = State()
    waiting_for_email = State()

def is_valid_email(email: str) -> bool:
    """Проверяет корректность email адреса"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def is_valid_phone(phone: str) -> bool:
    """Проверяет корректность номера телефона"""
    # Удаляем все не цифры из номера
    cleaned_phone = re.sub(r'\D', '', phone)
    # Проверяем длину и начало номера
    return len(cleaned_phone) >= 10 and len(cleaned_phone) <= 15

def format_phone(phone: str) -> str:
    """Форматирует номер телефона в стандартный вид"""
    cleaned_phone = re.sub(r'\D', '', phone)
    if cleaned_phone.startswith('8'):
        cleaned_phone = '7' + cleaned_phone[1:]
    if not cleaned_phone.startswith('7'):
        cleaned_phone = '7' + cleaned_phone
    return f"+{cleaned_phone}"

# Кнопка для получения инвайт-ссылки
def get_invite_button() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="Получить ссылку", callback_data="get_invite_link")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext):
    """Обработчик команды /start"""
    try:
        user_id = message.from_user.id
        user = await get_user_by_telegram_id(user_id, session)
        
        if user:
            await message.answer(
                "✅ Вы уже зарегистрированы!\n"
                "Используйте /info для просмотра информации о себе."
            )
            return
            
        # Создаем клавиатуру с кнопкой для отправки номера телефона
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]
            ],
            resize_keyboard=True
        )
        
        await message.answer(
            "👋 Добро пожаловать!\n\n"
            "Для регистрации нам нужен ваш номер телефона.\n"
            "Пожалуйста, нажмите на кнопку ниже 👇",
            reply_markup=keyboard
        )
        
        await state.set_state(UserRegistration.waiting_for_phone)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке команды start: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@router.message(UserRegistration.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    """Обработка номера телефона"""
    if not message.contact or not message.contact.phone_number:
        await message.answer(
            "❌ Пожалуйста, используйте кнопку для отправки номера телефона."
        )
        return

    # Сохраняем номер телефона
    await state.update_data(phone=message.contact.phone_number)
    
    # Убираем клавиатуру с кнопкой телефона
    await message.answer(
        "📧 Теперь, пожалуйста, введите ваш email адрес:",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await state.set_state(UserRegistration.waiting_for_email)

@router.message(UserRegistration.waiting_for_email)
async def process_email(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка email"""
    try:
        email = message.text.lower().strip()

        if not is_valid_email(email):
            await message.answer(
                "❌ Некорректный формат email.\n"
                "Пожалуйста, введите корректный email адрес.\n"
                "Пример: user@example.com"
            )
            return

        user_data = await state.get_data()
        phone = user_data.get("phone")
        
        # Проверяем, не существует ли уже пользователь с таким telegram_id
        existing_user = await get_user_by_telegram_id(message.from_user.id, session)
        if existing_user:
            await message.answer(
                "❌ Вы уже зарегистрированы!\n"
                "Используйте /info для просмотра информации о себе."
            )
            await state.clear()
            return
        
        # Создаем пользователя
        user = await create_user(
            telegram_id=message.from_user.id,
            full_name=message.from_user.full_name,
            email=email,
            phone=phone,
            session=session
        )
        
        if not user:
            await message.answer(
                "❌ Этот email уже используется другим пользователем.\n"
                "Пожалуйста, введите другой email адрес."
            )
            return
        
        await message.answer(
            "✅ Регистрация успешно завершена!\n\n"
            "📋 Ваши данные:\n"
            f"👤 Имя: {user.full_name}\n"
            f"📱 Телефон: {user.phone}\n"
            f"📧 Email: {user.email}\n\n"
            "Используйте /info для просмотра информации о себе."
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при обработке email: {e}")
        await message.answer(
            "❌ Произошла ошибка при регистрации.\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору."
        )
        await state.clear()

@router.callback_query(F.data == "get_invite_link")
async def handle_invite_callback(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """Обработчик нажатия на кнопку получения инвайт-ссылки"""
    try:
        # Создаем новое сообщение для обработки
        message = callback.message
        message.from_user = callback.from_user
        
        # Передаем управление в обработчик invite
        await cmd_invite(message, session, bot)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в обработчике invite callback: {e}")
        await callback.message.answer(
            "❌ Произошла ошибка при получении ссылки.\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору."
        )
        await callback.answer()
