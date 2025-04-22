from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from models import Subscription, InviteLink, User
from aiogram import Bot
import asyncio
import logging
import os
from dotenv import load_dotenv
import secrets
import string

logger = logging.getLogger(__name__)
load_dotenv()

# Получаем ID канала из переменных окружения
CHAT_ID = int(os.getenv("CHAT_ID", "0"))
if CHAT_ID == 0:
    logger.error("CHAT_ID not found in environment variables")
    raise ValueError("CHAT_ID must be set in environment variables")

def generate_invite_code(length: int = 8) -> str:
    """Генерирует уникальный код для инвайт-ссылки"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

async def create_subscription(session: AsyncSession, user_id: int, duration_days: int) -> Subscription:
    """Создает новую подписку для пользователя"""
    try:
        # Деактивируем все текущие подписки пользователя
        current_subs = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.is_active == True
            )
        )
        for sub in current_subs.scalars():
            sub.is_active = False

        # Создаем новую подписку
        start_date = datetime.now()
        end_date = start_date + timedelta(days=duration_days)
        
        subscription = Subscription(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )
        
        # Обновляем статус подписки у пользователя
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar_one()
        user.is_subscribed = True
        
        session.add(subscription)
        await session.commit()
        
        logger.info(f"Создана новая подписка для пользователя {user_id} на {duration_days} дней")
        return subscription
        
    except Exception as e:
        logger.error(f"Ошибка при создании подписки: {e}")
        await session.rollback()
        raise

async def check_subscription_status(session: AsyncSession, user_id: int) -> tuple[bool, int]:
    """Проверяет статус подписки пользователя"""
    try:
        # Сначала проверяем, есть ли пользователь
        user_query = select(User).where(User.id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"Пользователь {user_id} не найден при проверке подписки")
            return False, 0

        # Проверяем активную подписку
        query = select(Subscription).where(
            and_(
                Subscription.user_id == user_id,
                Subscription.is_active == True
            )
        )
        result = await session.execute(query)
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.info(f"У пользователя {user_id} нет активной подписки")
            return False, 0

        now = datetime.now()
        if subscription.end_date <= now:
            logger.info(f"Подписка пользователя {user_id} истекла")
            subscription.is_active = False
            await session.commit()
            return False, 0

        days_left = (subscription.end_date - now).days
        logger.info(f"У пользователя {user_id} активная подписка, осталось {days_left} дней")
        return True, days_left

    except Exception as e:
        logger.error(f"Ошибка при проверке статуса подписки пользователя {user_id}: {e}")
        return False, 0

async def generate_invite_link(session: AsyncSession, user_id: int, bot: Bot) -> str:
    """Генерирует инвайт-ссылку для пользователя"""
    try:
        # Получаем пользователя
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error(f"User {user_id} not found")
            return None

        # Проверяем статус подписки
        is_subscribed, _ = await check_subscription_status(session, user_id)
        if not is_subscribed:
            logger.error(f"User {user_id} does not have active subscription")
            return None
            
        try:
            # Проверяем права бота в канале
            bot_member = await bot.get_chat_member(chat_id=CHAT_ID, user_id=bot.id)
            
            if not bot_member.can_invite_users:
                logger.error(f"Bot doesn't have invite rights in chat {CHAT_ID}")
                return None
                
            # Создаем инвайт-ссылку через API Telegram
            invite_link = await bot.create_chat_invite_link(
                chat_id=CHAT_ID,
                member_limit=1,
                expire_date=datetime.now() + timedelta(days=1)
            )
            
            # Сохраняем ссылку в базе данных
            new_invite = InviteLink(
                user_id=user.id,
                link=invite_link.invite_link,
                chat_id=str(CHAT_ID),
                is_used=False
            )
            
            session.add(new_invite)
            await session.commit()
            
            logger.info(f"Created invite link for user {user_id}")
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