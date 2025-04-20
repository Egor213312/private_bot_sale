from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from models import Subscription, InviteLink, User
from aiogram import Bot
import asyncio
import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

# Получаем ID канала из переменных окружения
CHAT_ID = os.getenv("CHAT_ID")
PRIVATE_CHANNEL_ID = os.getenv("PRIVATE_CHANNEL_ID")

# Используем CHAT_ID или PRIVATE_CHANNEL_ID
TARGET_CHAT = CHAT_ID or PRIVATE_CHANNEL_ID
if not TARGET_CHAT:
    logger.error("Neither CHAT_ID nor PRIVATE_CHANNEL_ID found in environment variables")
    raise ValueError("Either CHAT_ID or PRIVATE_CHANNEL_ID must be set in environment variables")

# Преобразуем CHAT_ID в int, если это число
try:
    TARGET_CHAT = int(TARGET_CHAT)
except ValueError:
    # Если это не число (например, @channel_name), оставляем как есть
    pass

async def create_subscription(session: AsyncSession, user_id: int, duration_days: int) -> Subscription:
    """Создает новую подписку для пользователя"""
    try:
        start_date = datetime.now()
        end_date = start_date + timedelta(days=duration_days)
        
        subscription = Subscription(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )
        
        session.add(subscription)
        await session.commit()
        return subscription
        
    except Exception as e:
        logger.error(f"Ошибка при создании подписки: {e}")
        await session.rollback()
        raise

async def check_subscription_status(session: AsyncSession, user_id: int) -> tuple[bool, int]:
    """Проверяет статус подписки пользователя"""
    try:
        query = select(Subscription).where(
            and_(
                Subscription.user_id == user_id,
                Subscription.is_active == True
            )
        )
        result = await session.execute(query)
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            return False, 0
            
        days_left = (subscription.end_date - datetime.now()).days
        return days_left > 0, days_left
        
    except Exception as e:
        logger.error(f"Ошибка при проверке подписки: {e}")
        return False, 0

async def generate_invite_link(session: AsyncSession, user_id: int, bot: Bot) -> str:
    """Генерирует инвайт-ссылку для пользователя"""
    try:
        # Получаем пользователя
        query = select(User).where(User.telegram_id == user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error(f"User {user_id} not found")
            return None
            
        try:
            # Проверяем права бота в канале
            bot_member = await bot.get_chat_member(chat_id=TARGET_CHAT, user_id=bot.id)
            logger.info(f"Bot permissions in chat: {bot_member.permissions if hasattr(bot_member, 'permissions') else 'No permissions info'}")
            
            if not bot_member.can_invite_users:
                logger.error("Bot doesn't have rights to create invite links")
                return None
                
            # Создаем инвайт-ссылку через API Telegram
            invite_link = await bot.create_chat_invite_link(
                chat_id=TARGET_CHAT,
                member_limit=1,
                expire_date=datetime.now() + timedelta(days=1)
            )
            
            # Сохраняем ссылку в базе данных
            new_invite = InviteLink(
                user_id=user.id,
                link=invite_link.invite_link,
                chat_id=str(TARGET_CHAT),
                is_used=False
            )
            
            session.add(new_invite)
            await session.commit()
            
            return invite_link.invite_link
            
        except Exception as e:
            logger.error(f"Telegram API error: {str(e)}")
            return None
        
    except Exception as e:
        logger.error(f"Error generating invite link: {str(e)}")
        await session.rollback()
        return None

async def check_expiring_subscriptions(session: AsyncSession, bot: Bot):
    """Проверяет истекающие подписки"""
    try:
        query = select(Subscription).where(
            and_(
                Subscription.end_date <= datetime.now() + timedelta(days=1),
                Subscription.is_active == True
            )
        )
        result = await session.execute(query)
        subscriptions = result.scalars().all()
        
        for subscription in subscriptions:
            try:
                await bot.send_message(
                    subscription.user_id,
                    "Ваша подписка истекает через 24 часа. Пожалуйста, продлите её."
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления пользователю {subscription.user_id}: {e}")
                
    except Exception as e:
        logger.error(f"Ошибка при проверке истекающих подписок: {e}")

async def start_subscription_checker(session: AsyncSession, bot: Bot):
    """Запускает периодическую проверку подписок"""
    while True:
        try:
            await check_expiring_subscriptions(session, bot)
        except Exception as e:
            logger.error(f"Ошибка в фоновой проверке подписок: {e}")
        await asyncio.sleep(3600)  # Проверка каждый час 