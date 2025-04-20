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

logger = logging.getLogger(__name__)
router = Router()

class UserRegistration(StatesGroup):
    waiting_for_phone = State()
    waiting_for_email = State()

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
                "Вы уже зарегистрированы! Используйте /info для просмотра информации о себе."
            )
            return
            
        # Создаем клавиатуру с кнопкой для отправки номера телефона
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Отправить номер телефона", request_contact=True)]
            ],
            resize_keyboard=True
        )
        
        await message.answer(
            "Добро пожаловать! Для регистрации нам нужен ваш номер телефона. "
            "Пожалуйста, нажмите на кнопку ниже.",
            reply_markup=keyboard
        )
        
        await state.set_state(UserRegistration.waiting_for_phone)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке команды start: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

@router.message(UserRegistration.waiting_for_phone, F.contact)
async def process_phone(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка номера телефона"""
    try:
        phone = message.contact.phone_number
        await state.update_data(phone=phone)
        
        await message.answer(
            "Отлично! Теперь введите ваш email:",
            reply_markup=ReplyKeyboardRemove()
        )
        
        await state.set_state(UserRegistration.waiting_for_email)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке номера телефона: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

@router.message(UserRegistration.waiting_for_email)
async def process_email(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка email"""
    try:
        email = message.text
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
            "Регистрация успешно завершена! Используйте /info для просмотра информации о себе."
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при обработке email: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")


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
