from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select
from models import User, Subscription, InviteLink
from utils.subscription_manager import generate_invite_code
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("invite"))
async def cmd_invite(message: Message, session: AsyncSession):
    """Обработчик команды /invite"""
    try:
        # Получаем пользователя
        user_query = select(User).where(User.telegram_id == message.from_user.id)
        result = await session.execute(user_query)
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("❌ Вы не зарегистрированы в системе. Используйте команду /start")
            return

        # Проверяем, есть ли у пользователя активная подписка
        sub_query = select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.is_active == True
        )
        sub_result = await session.execute(sub_query)
        subscription = sub_result.scalar_one_or_none()

        if not subscription:
            await message.answer(
                "❌ У вас нет активной подписки.\n"
                "Для получения инвайт-ссылки необходимо приобрести подписку."
            )
            return

        # Создаем новую инвайт-ссылку
        invite_link = InviteLink(
            user_id=user.id,
            code=generate_invite_code(),
            is_used=False,
            created_at=datetime.now()
        )
        
        # Добавляем ссылку в базу данных
        session.add(invite_link)
        await session.commit()

        # Формируем полную ссылку
        full_link = f"https://t.me/{message.bot.username}?start={invite_link.code}"

        # Отправляем сообщение с инвайт-ссылкой
        await message.answer(
            "🎁 Ваша инвайт-ссылка:\n\n"
            f"<code>{full_link}</code>\n\n"
            "📝 Отправьте эту ссылку другу, чтобы пригласить его в бота.\n"
            "⚠️ Ссылка действительна только для одного использования.",
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке команды invite: {e}")
        await message.answer("❌ Произошла ошибка при создании инвайт-ссылки.")
