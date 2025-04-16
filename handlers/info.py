from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states import Registration
from models import User
from database import async_session
from sqlalchemy import select
from aiogram.filters import Command
@router.message(Command("info"))
async def cmd_info(message: Message):
    telegram_id = message.from_user.id

    async with async_session() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            status = "✅ Активна" if user.is_subscribed else "❌ Не активна"
            await message.answer(
                f"📄 Ваш профиль:\n"
                f"🆔 ID: {user.telegram_id}\n"
                f"👤 Имя: {user.full_name}\n"
                f"📧 Email: {user.email}\n\n"
                f"📌 Подписка:\n{status}\n"
                f"💳 Для активации используйте /buy"
            )
        else:
            await message.answer("Вы еще не зарегистрированы. Используйте /start.")