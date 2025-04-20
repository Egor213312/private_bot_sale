from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from db import get_user_by_telegram_id, create_user
from states import RegistrationState
from sqlalchemy.ext.asyncio import AsyncSession
from utils.subscription_manager import check_subscription_status
from handlers.invite import handle_invite_request
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
async def process_phone(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка номера телефона"""
    try:
        if message.contact:
            phone = message.contact.phone_number
        else:
            phone = message.text

        if not phone:
            await message.answer(
                "❌ Пожалуйста, отправьте номер телефона, используя кнопку ниже или введите его вручную.\n"
                "Формат: +7XXXXXXXXXX"
            )
            return

        if not is_valid_phone(phone):
            await message.answer(
                "❌ Некорректный формат номера телефона.\n"
                "Пожалуйста, используйте кнопку или введите номер в формате: +7XXXXXXXXXX"
            )
            return

        formatted_phone = format_phone(phone)
        await state.update_data(phone=formatted_phone)
        
        await message.answer(
            "✅ Номер телефона принят!\n\n"
            "Теперь введите ваш email:",
            reply_markup=ReplyKeyboardRemove()
        )
        
        await state.set_state(UserRegistration.waiting_for_email)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке номера телефона: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

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
        
        # Создаем пользователя
        user = await create_user(
            telegram_id=message.from_user.id,
            full_name=message.from_user.full_name,
            email=email,
            phone=phone,
            session=session
        )
        
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
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.callback_query(F.data == "get_invite_link")
async def handle_invite_callback(callback: CallbackQuery, session: AsyncSession):
    """Обработчик нажатия на кнопку получения инвайт-ссылки"""
    try:
        # Передаем управление в обработчик invite
        await handle_invite_request(callback.message, session)
        await callback.answer()
    except Exception as e:
        await callback.message.answer(
            "❌ Произошла ошибка при получении ссылки.\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору."
        )
        print(f"Ошибка в обработчике invite callback: {e}")
        await callback.answer()


@router.message(RegistrationState.full_name)
async def process_full_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("Введите ваш email:")
    await state.set_state(RegistrationState.email)


@router.message(RegistrationState.email)
async def process_email(message: Message, state: FSMContext, session: AsyncSession):
    try:
        user_data = await state.get_data()
        full_name = user_data.get("full_name")
        email = message.text

        # Создаем пользователя
        user = await create_user(
            telegram_id=message.from_user.id,
            full_name=full_name,
            email=email,
            session=session
        )

        await message.answer(
            "✅ Регистрация успешно завершена!\n\n"
            "Теперь вы можете:\n"
            "1. Активировать подписку командой /buy\n"
            "2. Проверить статус подписки командой /subscription"
        )
        await state.clear()

    except Exception as e:
        await message.answer(
            "❌ Произошла ошибка при регистрации.\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору."
        )
        print(f"Ошибка при регистрации пользователя: {e}")
        await state.clear()
