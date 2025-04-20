from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User
from utils.subscription_manager import create_subscription, generate_invite_link
import logging
import os

logger = logging.getLogger(__name__)
router = Router()

# ID администратора
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id == ADMIN_ID

def get_user_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру с действиями для пользователя"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="❌ Удалить",
                callback_data=f"delete_user_{user_id}"
            ),
            InlineKeyboardButton(
                text="✅ Выдать подписку",
                callback_data=f"give_subscription_{user_id}"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession):
    """Обработчик команды /admin"""
    try:
        if not is_admin(message.from_user.id):
            await message.answer("У вас нет доступа к этой команде.")
            return
            
        # Получаем всех пользователей
        query = select(User)
        result = await session.execute(query)
        users = result.scalars().all()
        
        if not users:
            await message.answer("👥 Пользователей пока нет.")
            return
            
        # Отправляем информацию о каждом пользователе отдельным сообщением с кнопками
        for user in users:
            user_info = (
                f"👤 Список пользователей:\n\n"
                f"ID: {user.telegram_id}\n"
                f"Имя: {user.full_name}\n"
                f"Email: {user.email}\n"
                f"Подписка: {'✅' if user.is_subscribed else '❌'}"
            )
            
            # Создаем клавиатуру для пользователя
            keyboard = get_user_keyboard(user.id)
            
            # Отправляем сообщение с информацией о пользователе и кнопками
            await message.answer(user_info, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке команды admin: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

@router.callback_query(F.data.startswith("delete_user_"))
async def process_delete_user(callback: CallbackQuery, session: AsyncSession):
    """Обработка удаления пользователя"""
    try:
        if not is_admin(callback.from_user.id):
            await callback.answer("У вас нет доступа к этой команде.")
            return
            
        user_id = int(callback.data.split("_")[2])
        user = await session.get(User, user_id)
        
        if user:
            await session.delete(user)
            await session.commit()
            await callback.message.edit_text(
                f"Пользователь {user.full_name} удален.",
                reply_markup=None
            )
        else:
            await callback.answer("Пользователь не найден.")
            
    except Exception as e:
        logger.error(f"Ошибка при удалении пользователя: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.")

@router.callback_query(F.data.startswith("give_subscription_"))
async def process_give_subscription(callback: CallbackQuery, session: AsyncSession):
    """Обработка выдачи подписки"""
    try:
        if not is_admin(callback.from_user.id):
            await callback.answer("У вас нет доступа к этой команде.")
            return
            
        user_id = int(callback.data.split("_")[2])
        user = await session.get(User, user_id)
        
        if user:
            # Создаем подписку на 30 дней
            await create_subscription(session, user.id, 30)
            user.is_subscribed = True
            await session.commit()
            
            # Обновляем сообщение с информацией о пользователе
            user_info = (
                f"👤 Список пользователей:\n\n"
                f"ID: {user.telegram_id}\n"
                f"Имя: {user.full_name}\n"
                f"Email: {user.email}\n"
                f"Подписка: ✅\n\n"
                f"✅ Подписка успешно выдана!"
            )
            
            await callback.message.edit_text(
                user_info,
                reply_markup=get_user_keyboard(user.id)
            )
            
        else:
            await callback.answer("Пользователь не найден.")
            
    except Exception as e:
        logger.error(f"Ошибка при выдаче подписки: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.")