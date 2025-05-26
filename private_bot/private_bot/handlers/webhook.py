from aiohttp import web
from yookassa import Configuration, Payment
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from utils.subscription_manager import create_subscription
from db import get_user_by_id
import os

logger = logging.getLogger(__name__)

# Настройки ЮKassa
SHOP_ID = os.getenv("YOKASSA_SHOP_ID")
SECRET_KEY = os.getenv("YOKASSA_SECRET_KEY")

Configuration.account_id = SHOP_ID
Configuration.secret_key = SECRET_KEY

async def handle_webhook(request):
    """Обработчик уведомлений от ЮKassa"""
    try:
        # Получаем данные уведомления
        data = await request.json()
        
        # Проверяем тип уведомления
        if data['event'] != 'payment.succeeded':
            return web.Response(status=200)
            
        # Получаем данные платежа
        payment_id = data['object']['id']
        payment = Payment.find_one(payment_id)
        
        if payment.status != 'succeeded':
            return web.Response(status=200)
            
        # Получаем метаданные платежа
        metadata = payment.metadata
        user_id = metadata.get('user_id')
        months = metadata.get('months')
        
        if not user_id or not months:
            logger.error(f"Missing metadata in payment {payment_id}")
            return web.Response(status=200)
            
        # Создаем сессию базы данных
        async with AsyncSession() as session:
            # Получаем пользователя
            user = await get_user_by_id(session, user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return web.Response(status=200)
                
            # Создаем подписку
            await create_subscription(session, user_id, months * 30)
            
            # Обновляем статус подписки пользователя
            user.is_subscribed = True
            await session.commit()
            
            # Отправляем уведомление пользователю
            # Это нужно реализовать через бота
            
        return web.Response(status=200)
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return web.Response(status=500)

# Создаем маршрут для вебхука
routes = web.RouteTableDef()

@routes.post('/webhook/payment')
async def webhook_handler(request):
    return await handle_webhook(request) 