from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_user_by_telegram_id
import logging
import os
from yookassa import Configuration, Payment
from datetime import datetime, timedelta
from utils.subscription_manager import create_subscription

logger = logging.getLogger(__name__)
router = Router()

# Настройки ЮKassa
SHOP_ID = os.getenv("YOKASSA_SHOP_ID")
SECRET_KEY = os.getenv("YOKASSA_SECRET_KEY")

# Настройка цен подписок (в рублях)
SUBSCRIPTION_PRICES = {
    "1_month": 1000,
    "3_months": 2700,
    "6_months": 5000,
    "12_months": 9000
}

def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с вариантами подписки"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="1 месяц - 1000₽",
                callback_data="buy_1_month"
            )
        ],
        [
            InlineKeyboardButton(
                text="3 месяца - 2700₽ (экономия 10%)",
                callback_data="buy_3_months"
            )
        ],
        [
            InlineKeyboardButton(
                text="6 месяцев - 5000₽ (экономия 17%)",
                callback_data="buy_6_months"
            )
        ],
        [
            InlineKeyboardButton(
                text="12 месяцев - 9000₽ (экономия 25%)",
                callback_data="buy_12_months"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command("buy"))
async def cmd_buy(message: Message, session: AsyncSession):
    """Обработчик команды /buy"""
    try:
        user = await get_user_by_telegram_id(message.from_user.id, session)
        if not user:
            await message.answer(
                "❌ Вы не зарегистрированы.\n"
                "Используйте команду /start для регистрации."
            )
            return

        await message.answer(
            "💎 Выберите период подписки:\n\n"
            "Что включено в подписку:\n"
            "✅ Доступ к закрытому каналу\n"
            "✅ Возможность создавать инвайт-ссылки\n"
            "✅ Поддержка 24/7\n",
            reply_markup=get_subscription_keyboard()
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке команды buy: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@router.callback_query(lambda c: c.data.startswith('buy_'))
async def process_buy(callback: CallbackQuery, session: AsyncSession):
    """Обработка выбора периода подписки"""
    try:
        user = await get_user_by_telegram_id(callback.from_user.id, session)
        if not user:
            await callback.answer("Вы не зарегистрированы!")
            return

        # Получаем период подписки из callback_data
        period = callback.data.replace('buy_', '')
        price = SUBSCRIPTION_PRICES.get(period)
        months = int(period.split('_')[0])

        if not price:
            await callback.answer("Неверный период подписки!")
            return

        try:
            # Настраиваем ЮKassa
            Configuration.account_id = SHOP_ID
            Configuration.secret_key = SECRET_KEY

            # Создаем платеж
            payment = Payment.create({
                "amount": {
                    "value": str(price),
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"https://t.me/{(await callback.bot.me()).username}"
                },
                "capture": True,
                "description": f"Подписка на {months} месяц(ев) для пользователя {user.full_name}",
                "metadata": {
                    "user_id": user.id,
                    "telegram_id": user.telegram_id,
                    "months": months
                }
            })

            # Создаем клавиатуру с кнопкой оплаты
            pay_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="💳 Перейти к оплате",
                    url=payment.confirmation.confirmation_url
                )
            ]])

            await callback.message.edit_text(
                f"💳 Счет на оплату:\n\n"
                f"Период: {months} месяц(ев)\n"
                f"Сумма: {price}₽\n\n"
                "Для оплаты нажмите на кнопку ниже 👇",
                reply_markup=pay_keyboard
            )

        except Exception as e:
            logger.error(f"Ошибка при создании платежа: {e}")
            await callback.message.edit_text(
                "❌ Ошибка при создании платежа.\n"
                "Пожалуйста, попробуйте позже или обратитесь к администратору."
            )

    except Exception as e:
        logger.error(f"Ошибка при обработке оплаты: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.") 