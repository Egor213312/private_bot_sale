from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import async_session
from models import User
from sqlalchemy import select, delete
import os

router = Router()

# Клавиатура для удаления пользователя
def get_delete_keyboard(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Удалить", callback_data=f"delete_{user_id}")
    return builder.as_markup()

# Админ-панель
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    admin_id = int(os.getenv("ADMIN_ID"))
    if message.from_user.id != admin_id:
        await message.answer("⛔ У вас нет доступа к этой команде")
        return

    async with async_session() as session:
        stmt = select(User)
        result = await session.execute(stmt)
        users = result.scalars().all()

    if not users:
        await message.answer("📭 Нет зарегистрированных пользователей")
        return

    text = "📊 Список пользователей:\n\n"
    for user in users:
        status = "✅" if user.is_subscribed else "❌"
        text += (
            f"ID: {user.telegram_id}\n"
            f"Имя: {user.full_name}\n"
            f"Email: {user.email}\n"
            f"Подписка: {status}\n"
        )
        await message.answer(
            text,
            reply_markup=get_delete_keyboard(user.telegram_id)
        )
        text = ""

# Обработка удаления пользователя
@router.callback_query(F.data.startswith("delete_"))
async def delete_user(callback: CallbackQuery):
    admin_id = int(os.getenv("ADMIN_ID"))
    if callback.from_user.id != admin_id:
        await callback.answer("⛔ Нет прав для удаления", show_alert=True)
        return

    user_id = int(callback.data.split("_")[1])
    
    async with async_session() as session:
        stmt = delete(User).where(User.telegram_id == user_id)
        await session.execute(stmt)
        await session.commit()
    
    await callback.message.edit_text(
        f"🗑 Пользователь ID {user_id} удален",
        reply_markup=None
    )
    await callback.answer()