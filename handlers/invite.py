from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_user_by_telegram_id
from utils.subscription_manager import generate_invite_link
import logging

logger = logging.getLogger(__name__)
router = Router()

async def handle_invite_request(message: Message, session: AsyncSession, bot: Bot) -> None:
    """Обработка запроса на получение инвайт-ссылки"""
    try:
        user_id = message.from_user.id
        user = await get_user_by_telegram_id(user_id, session)
        
        if not user:
            await message.answer(
                "❌ Вы не зарегистрированы.\n"
                "Используйте команду /start для регистрации."
            )
            return
            
        if not user.is_subscribed:
            await message.answer(
                "❌ У вас нет активной подписки.\n"
                "Пожалуйста, обратитесь к администратору для получения подписки."
            )
            return
            
        # Генерируем инвайт-ссылку
        invite_link = await generate_invite_link(session, user_id, bot)
        
        if invite_link:
            await message.answer(
                "✅ Ваша инвайт-ссылка успешно создана!\n\n"
                f"🔗 Ссылка: {invite_link}\n\n"
                "⚠️ Важно:\n"
                "- Ссылка действительна 24 часа\n"
                "- Может быть использована только один раз"
            )
        else:
            await message.answer(
                "❌ Не удалось сгенерировать инвайт-ссылку.\n"
                "Пожалуйста, попробуйте позже или обратитесь к администратору."
            )
            
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса инвайт-ссылки: {e}")
        await message.answer(
            "❌ Произошла ошибка при создании инвайт-ссылки.\n"
            "Пожалуйста, попробуйте позже."
        )

@router.message(Command("invite"))
async def handle_invite_command(message: Message, session: AsyncSession, bot: Bot) -> None:
    """Обработчик команды /invite"""
    await handle_invite_request(message, session, bot)
