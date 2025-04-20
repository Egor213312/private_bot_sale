from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_user_by_telegram_id
from utils.subscription_manager import check_subscription_status
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("info"))
async def cmd_info(message: Message, session: AsyncSession):
    """Обработчик команды /info"""
    try:
        user = await get_user_by_telegram_id(message.from_user.id, session)
        
        if not user:
            await message.answer("Вы не зарегистрированы. Используйте /start для регистрации.")
            return
            
        # Проверяем статус подписки
        is_subscribed, days_left = await check_subscription_status(session, user.id)
        
        # Формируем сообщение с информацией
        info_message = (
            f"👤 Информация о пользователе:\n\n"
            f"ID: {user.telegram_id}\n"
            f"Имя: {user.full_name}\n"
            f"Email: {user.email}\n"
            f"Телефон: {user.phone}\n"
            f"Статус подписки: {'Активна' if is_subscribed else 'Неактивна'}\n"
        )
        
        if is_subscribed:
            info_message += f"Дней осталось: {days_left}\n"
            
        await message.answer(info_message)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке команды info: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")