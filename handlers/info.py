from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from models import User
from database import async_session
from sqlalchemy import select
from datetime import datetime

router = Router()

@router.message(Command("info"))
async def cmd_info(message: Message):
    """Показывает информацию о пользователе"""
    async with async_session() as session:
        # Получаем пользователя из БД
        user = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = user.scalar_one_or_none()

        if not user:
            await message.answer("ℹ️ Вы еще не зарегистрированы. Используйте /start")
            return

        # Форматируем дату подписки
        sub_status = "❌ Не активна"
        if user.is_subscribed:
            sub_status = "✅ Активна"
            if user.subscription_expires:
                sub_status += f" (до {user.subscription_expires.strftime('%d.%m.%Y')}"

        # Формируем ответ
        response = (
            f"📋 Ваш профиль:\n\n"
            f"🆔 ID: {user.telegram_id}\n"
            f"👤 Имя: {user.full_name}\n"
            f"📧 Email: {user.email}\n"
            f"🔐 Подписка: {sub_status}"
        )

        await message.answer(response)