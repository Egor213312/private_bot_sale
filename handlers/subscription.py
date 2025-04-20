from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from utils.subscription_manager import (
    create_subscription,
    check_subscription_status,
    generate_invite_link
)
from models import User
from sqlalchemy import select
from db import get_user_by_telegram_id
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("info"))
async def handle_subscription_info(message: Message, session: AsyncSession):
    """Обработчик команды /info"""
    try:
        # Получаем пользователя
        user = await get_user_by_telegram_id(message.from_user.id, session)
        if not user:
            await message.answer("Вы не зарегистрированы. Используйте команду /start")
            return
            
        # Проверяем статус подписки
        is_active, days_left = await check_subscription_status(session, user.id)
        
        if is_active:
            await message.answer(
                f"✅ Ваша подписка активна\n"
                f"Осталось дней: {days_left}"
            )
        else:
            await message.answer(
                "❌ У вас нет активной подписки\n"
                "Используйте команду /buy для активации подписки."
            )
            
    except Exception as e:
        logger.error(f"Ошибка в обработчике subscription_info: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

@router.message(Command("invite"))
async def handle_invite_request(message: Message, session: AsyncSession):
    """Генерирует инвайт-ссылку для пользователя"""
    query = select(User).where(User.telegram_id == message.from_user.id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("Вы не зарегистрированы. Используйте команду /start")
        return
    
    is_active, _ = await check_subscription_status(session, user.id)
    
    if not is_active:
        await message.answer(
            "❌ У вас нет активной подписки.\n"
            "Используйте команду /buy для активации подписки."
        )
        return
    
    # Здесь нужно указать ID вашего закрытого чата/канала
    CHAT_ID = "YOUR_CHAT_ID"
    
    try:
        invite_link = await generate_invite_link(message.bot, session, user.id, CHAT_ID)
        await message.answer(
            f"🔗 Ваша инвайт-ссылка:\n{invite_link}\n\n"
            "⚠️ Ссылка одноразовая и действительна 24 часа."
        )
    except Exception as e:
        await message.answer(
            "❌ Произошла ошибка при генерации ссылки.\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору."
        )
        print(f"Ошибка при генерации инвайт-ссылки: {e}")

# Обработчик успешной оплаты
@router.callback_query(F.data.startswith("payment_success:"))
async def handle_payment_success(callback: CallbackQuery, session: AsyncSession):
    """Обрабатывает успешную оплату подписки"""
    user_id = int(callback.data.split(":")[1])
    duration_days = 30  # или получать из callback.data
    
    try:
        await create_subscription(session, user_id, duration_days)
        await callback.message.answer(
            "✅ Подписка успешно активирована!\n\n"
            "Теперь вы можете:\n"
            "1. Получить инвайт-ссылку командой /invite\n"
            "2. Проверить статус подписки командой /subscription"
        )
    except Exception as e:
        await callback.message.answer(
            "❌ Произошла ошибка при активации подписки.\n"
            "Пожалуйста, обратитесь к администратору."
        )
        print(f"Ошибка при активации подписки: {e}")
    
    await callback.answer() 