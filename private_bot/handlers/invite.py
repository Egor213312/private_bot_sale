from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select
from models import User, Subscription, InviteLink
from utils.subscription_manager import generate_invite_code, check_subscription_status, generate_invite_link
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)
router = Router()
BOT_USERNAME = os.getenv("BOT_USERNAME")

async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    """Получает пользователя по telegram_id"""
    try:
        async with session.begin_nested():
            query = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя: {e}")
        return None

@router.message(Command("invite"))
async def cmd_invite(message: Message, session: AsyncSession, bot: Bot) -> None:
    """Обработчик команды /invite"""
    try:
        # Получаем пользователя
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("❌ Вы не зарегистрированы в системе. Используйте /start для регистрации.")
            return

        # Проверяем наличие активной подписки
        is_subscribed, _ = await check_subscription_status(session, user.id)
        if not is_subscribed:
            await message.answer(
                "❌ У вас нет активной подписки.\n"
                "Используйте /subscription для получения подписки."
            )
            return

        # Генерируем инвайт-ссылку
        invite_link = await generate_invite_link(session, user.id, bot)
        
        if not invite_link:
            await message.answer(
                "❌ Произошла ошибка при создании приглашения.\n"
                "Пожалуйста, попробуйте позже или обратитесь к администратору."
            )
            return

        # Отправляем сообщение с ссылкой
        await message.answer(
            f"🎁 Ваша инвайт-ссылка в закрытый канал:\n\n"
            f"{invite_link}\n\n"
            f"⚠️ Ссылка действительна 24 часа и может быть использована только один раз.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📤 Поделиться", url=f"https://t.me/share/url?url={invite_link}")]
                ]
            )
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке команды invite: {e}")
        await message.answer(
            "❌ Произошла ошибка при создании приглашения.\n"
            "Пожалуйста, попробуйте позже."
        )
