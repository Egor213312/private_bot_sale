from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User, Subscription
from datetime import datetime
import asyncio
import logging
import os

logger = logging.getLogger(__name__)

CHAT_ID = int(os.getenv("CHAT_ID", "0"))

async def remove_expired_subscriptions(session: AsyncSession, bot: Bot):
    """Проверяет и удаляет пользователей с истекшей подпиской из канала"""
    try:
        # Получаем всех пользователей с подписками
        query = select(User).where(User.is_subscribed == True)
        result = await session.execute(query)
        users = result.scalars().all()

        current_time = datetime.now()
        
        for user in users:
            # Получаем активную подписку пользователя
            sub_query = select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.is_active == True
            )
            sub_result = await session.execute(sub_query)
            subscription = sub_result.scalar_one_or_none()

            if subscription and subscription.end_date <= current_time:
                try:
                    # Удаляем пользователя из канала
                    await bot.ban_chat_member(
                        chat_id=CHAT_ID,
                        user_id=user.telegram_id,
                        revoke_messages=False
                    )
                    
                    # Деактивируем подписку
                    subscription.is_active = False
                    user.is_subscribed = False
                    await session.commit()

                    # Уведомляем пользователя
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=(
                            "⚠️ <b>Ваша подписка истекла</b>\n\n"
                            "Вы были удалены из канала.\n"
                            "Для продления подписки используйте команду /buy"
                        ),
                        parse_mode="HTML"
                    )
                    
                    logger.info(f"Пользователь {user.telegram_id} удален из канала (истекла подписка)")
                
                except Exception as e:
                    logger.error(f"Ошибка при обработке пользователя {user.telegram_id}: {e}")

    except Exception as e:
        logger.error(f"Ошибка при проверке подписок: {e}")

async def start_subscription_checker(session: AsyncSession, bot: Bot):
    """Запускает периодическую проверку подписок"""
    while True:
        await remove_expired_subscriptions(session, bot)
        # Проверяем каждый час
        await asyncio.sleep(3600) 