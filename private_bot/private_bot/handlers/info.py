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
            await message.answer(
                "❌ Вы не зарегистрированы.\n"
                "Используйте /start для регистрации."
            )
            return
            
        # Проверяем статус подписки
        is_subscribed, days_left = await check_subscription_status(session, user.id)
        
        # Формируем статус подписки
        if is_subscribed:
            subscription_status = f"✅ Активна\n⏳ Дней осталось: {days_left}"
        else:
            subscription_status = "❌ Неактивна\n💡 Используйте /buy для покупки"
        
        # Формируем сообщение с информацией
        info_message = (
            "🔰 <b>Информация о пользователе</b>\n\n"
            f"📱 <b>ID:</b> <code>{user.telegram_id}</code>\n"
            f"👤 <b>Имя:</b> {user.full_name}\n"
            f"📧 <b>Email:</b> {user.email}\n"
            f"☎️ <b>Телефон:</b> {user.phone}\n\n"
            f"📊 <b>Статус подписки:</b>\n{subscription_status}\n\n"
            "📌 <b>Доступные команды:</b>\n"
            "• /buy - Купить подписку\n"
            "• /invite - Получить инвайт-ссылку\n"
            "• /info - Информация о профиле"
        )
            
        await message.answer(
            info_message,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке команды info: {e}")
        await message.answer(
            "❌ Произошла ошибка.\n"
            "Пожалуйста, попробуйте позже."
        )