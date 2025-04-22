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
from sqlalchemy.orm import joinedload

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

async def create_subscription(
    session: AsyncSession,
    user_id: int,
    duration_days: int,
    auto_renewal: bool = False
) -> Subscription:
    """Создает новую подписку для пользователя"""
    try:
        # Получаем пользователя
        user = await session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
            
        # Деактивируем все текущие подписки пользователя
        query = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.is_active == True
        )
        result = await session.execute(query)
        current_subscriptions = result.scalars().all()
        
        for sub in current_subscriptions:
            sub.is_active = False
        
        # Создаем новую подписку
        start_date = datetime.now()
        end_date = start_date + timedelta(days=duration_days)
        
        subscription = Subscription(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            is_active=True,
            auto_renewal=auto_renewal
        )
        
        # Добавляем подписку в сессию
        session.add(subscription)
        await session.commit()
        
        # Обновляем объекты
        await session.refresh(subscription)
        await session.refresh(user)
        
        logger.info(f"Создана новая подписка для пользователя {user_id}: {subscription}")
        return subscription
        
    except Exception as e:
        logger.error(f"Ошибка при создании подписки: {e}")
        raise e

async def check_subscription_status(session: AsyncSession, user_id: int) -> tuple[bool, int]:
    """
    Проверяет статус подписки пользователя
    Возвращает tuple[bool, int]:
    - bool: True если подписка активна, False если нет
    - int: количество оставшихся дней подписки (0 если подписка неактивна)
    """
    try:
        # Получаем пользователя с его подписками
        query = select(User).where(User.id == user_id).options(joinedload(User.subscriptions))
        result = await session.execute(query)
        user = result.unique().scalar_one_or_none()

        if not user:
            logger.error(f"Пользователь с id {user_id} не найден")
            return False, 0

        # Получаем все активные подписки
        active_subscriptions = [sub for sub in user.subscriptions if sub.is_active]
        
        if not active_subscriptions:
            return False, 0

        # Находим подписку с самой поздней датой окончания
        latest_subscription = max(active_subscriptions, key=lambda x: x.end_date)
        
        # Проверяем, не истекла ли подписка
        now = datetime.now()
        if latest_subscription.end_date < now:
            # Помечаем подписку как неактивную
            latest_subscription.is_active = False
            await session.commit()
            return False, 0

        # Вычисляем оставшиеся дни
        days_left = (latest_subscription.end_date - now).days
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
                code=generate_invite_code(),
                created_by_id=user.id,
                is_used=False,
                link=invite_link.invite_link
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