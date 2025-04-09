from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from database import async_session
from models import User
from sqlalchemy import select
import os

router = Router()

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    admin_id = int(os.getenv("ADMIN_ID"))
    if message.from_user.id != admin_id:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    async with async_session() as session:
        stmt = select(User)
        result = await session.execute(stmt)
        users = result.scalars().all()

    if not users:
        await message.answer("Пользователи не найдены.")
        return

    text = "📋 Список пользователей:\n\nID | Имя | Почта | Подписка\n-------------------------"
    for user in users:
        sub = "✅" if user.is_subscribed else "❌"
        text += f"\n{user.telegram_id} | {user.full_name} | {user.email} | {sub}"

    await message.answer(text)
