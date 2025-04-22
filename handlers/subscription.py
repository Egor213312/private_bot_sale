from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from utils.subscription_manager import (
    create_subscription,
    check_subscription_status,
    generate_invite_link
)
from models import User, Subscription
from sqlalchemy import select
from db import get_user_by_telegram_id
import logging
from datetime import datetime, timedelta
from config import SUBSCRIPTION_PRICES, PAYMENT_CARD, PAYMENT_RECEIVER

logger = logging.getLogger(__name__)
router = Router()

def get_subscription_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для управления подпиской"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="1 месяц",
                callback_data=f"sub_extend_{user_id}_30"
            ),
            InlineKeyboardButton(
                text="3 месяца",
                callback_data=f"sub_extend_{user_id}_90"
            )
        ],
        [
            InlineKeyboardButton(
                text="6 месяцев",
                callback_data=f"sub_extend_{user_id}_180"
            ),
            InlineKeyboardButton(
                text="1 год",
                callback_data=f"sub_extend_{user_id}_365"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с тарифами подписки"""
    keyboard = [
        [
            InlineKeyboardButton(
                text=f"1 месяц - {SUBSCRIPTION_PRICES[1]}₽",
                callback_data="buy_sub_1"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"3 месяца - {SUBSCRIPTION_PRICES[3]}₽",
                callback_data="buy_sub_3"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"12 месяцев - {SUBSCRIPTION_PRICES[12]}₽",
                callback_data="buy_sub_12"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command("info"))
async def handle_subscription_info(message: Message, session: AsyncSession):
    """Обработчик команды /info"""
    try:
        # Получаем пользователя
        user = await get_user_by_telegram_id(message.from_user.id, session)
        if not user:
            await message.answer("Вы не зарегистрированы. Используйте команду /start")
            return
            
        # Проверяем статус подписки
        is_active, days_left = await check_subscription_status(session, user.id)
        
        if is_active:
            await message.answer(
                f"✅ Ваша подписка активна\n"
                f"Осталось дней: {days_left}"
            )
        else:
            await message.answer(
                "❌ У вас нет активной подписки\n"
                "Используйте команду /buy для активации подписки."
            )
            
    except Exception as e:
        logger.error(f"Ошибка в обработчике subscription_info: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

@router.message(Command("invite"))
async def handle_invite_request(message: Message, session: AsyncSession):
    """Генерирует инвайт-ссылку для пользователя"""
    query = select(User).where(User.telegram_id == message.from_user.id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("Вы не зарегистрированы. Используйте команду /start")
        return
    
    is_active, _ = await check_subscription_status(session, user.id)
    
    if not is_active:
        await message.answer(
            "❌ У вас нет активной подписки.\n"
            "Используйте команду /buy для активации подписки."
        )
        return
    
    # Здесь нужно указать ID вашего закрытого чата/канала
    CHAT_ID = "YOUR_CHAT_ID"
    
    try:
        invite_link = await generate_invite_link(message.bot, session, user.id, CHAT_ID)
        await message.answer(
            f"🔗 Ваша инвайт-ссылка:\n{invite_link}\n\n"
            "⚠️ Ссылка одноразовая и действительна 24 часа."
        )
    except Exception as e:
        await message.answer(
            "❌ Произошла ошибка при генерации ссылки.\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору."
        )
        print(f"Ошибка при генерации инвайт-ссылки: {e}")

# Обработчик успешной оплаты
@router.callback_query(F.data.startswith("payment_success:"))
async def handle_payment_success(callback: CallbackQuery, session: AsyncSession):
    """Обрабатывает успешную оплату подписки"""
    user_id = int(callback.data.split(":")[1])
    duration_days = 30  # или получать из callback.data
    
    try:
        await create_subscription(session, user_id, duration_days)
        await callback.message.answer(
            "✅ Подписка успешно активирована!\n\n"
            "Теперь вы можете:\n"
            "1. Получить инвайт-ссылку командой /invite\n"
            "2. Проверить статус подписки командой /subscription"
        )
    except Exception as e:
        await callback.message.answer(
            "❌ Произошла ошибка при активации подписки.\n"
            "Пожалуйста, обратитесь к администратору."
        )
        print(f"Ошибка при активации подписки: {e}")
    
    await callback.answer()

@router.message(Command("subscription"))
async def cmd_subscription(message: Message, session: AsyncSession):
    """Показывает информацию о подписке и варианты продления"""
    try:
        user = await get_user_by_telegram_id(message.from_user.id, session)
        if not user:
            await message.answer(
                "❌ Вы не зарегистрированы.\n"
                "Используйте команду /start для регистрации."
            )
            return

        is_active, days_left = await check_subscription_status(session, user.id)
        
        # Получаем историю подписок
        subs_query = select(Subscription).where(Subscription.user_id == user.id).order_by(Subscription.start_date.desc())
        subs_result = await session.execute(subs_query)
        subscriptions = subs_result.scalars().all()
        
        # Формируем информацию о текущей подписке
        if is_active:
            current_sub = subscriptions[0] if subscriptions else None
            status_text = (
                f"✅ <b>Подписка активна</b>\n"
                f"⏳ Дней осталось: {days_left}\n"
                f"📅 Дата окончания: {current_sub.end_date.strftime('%d.%m.%Y')}\n"
                f"🔄 Автопродление: {'Включено' if current_sub and getattr(current_sub, 'auto_renewal', False) else 'Отключено'}"
            )
        else:
            last_sub = subscriptions[0] if subscriptions else None
            if last_sub:
                status_text = (
                    f"❌ <b>Подписка неактивна</b>\n"
                    f"📅 Последняя подписка закончилась: {last_sub.end_date.strftime('%d.%m.%Y')}"
                )
            else:
                status_text = "❌ <b>У вас ещё не было подписки</b>"
            
        # Формируем историю подписок
        history_text = ""
        if subscriptions:
            history_text = "\n<b>📋 История подписок:</b>\n"
            for sub in subscriptions[:3]:  # Последние 3 подписки
                duration = (sub.end_date - sub.start_date).days
                history_text += (
                    f"• {sub.start_date.strftime('%d.%m.%Y')} - {sub.end_date.strftime('%d.%m.%Y')}"
                    f" ({duration} дней)\n"
                )
        
        message_text = (
            f"👤 <b>Информация о подписке</b>\n\n"
            f"{status_text}\n\n"
            f"{history_text}\n"
            "💫 <b>Доступные периоды продления:</b>"
        )
        
        await message.answer(
            message_text,
            parse_mode="HTML",
            reply_markup=get_subscription_keyboard(user.id)
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении информации о подписке: {e}")
        await message.answer(
            "❌ Произошла ошибка при получении информации о подписке.\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору."
        )

@router.callback_query(F.data.startswith("sub_extend_"))
async def process_subscription_extend(callback: CallbackQuery, session: AsyncSession):
    """Обработка продления подписки"""
    try:
        _, user_id, days = callback.data.split("_")[1:]
        user_id, days = int(user_id), int(days)                                  
        
        # Здесь можно добавить логику оплаты
        # Пока просто показываем сообщение
        await callback.message.edit_text(
            f"💳 Для продления подписки на {days} дней:\n\n"
            "1. Переведите XXX рублей на карту:\n"
            "<code>1234 5678 9012 3456</code>\n\n"
            "2. Отправьте чек администратору @admin\n"
            "3. После проверки подписка будет активирована",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке продления подписки: {e}")
        await callback.answer("❌ Произошла ошибка. Попробуйте позже.")

@router.message(Command("buy"))
async def cmd_buy(message: Message, session: AsyncSession):
    """Обработчик команды /buy"""
    try:
        # Проверяем, есть ли у пользователя активная подписка
        is_active, days_left = await check_subscription_status(session, message.from_user.id)
        if is_active:
            await message.answer(
                f"У вас уже есть активная подписка!\n"
                f"Осталось дней: {days_left}"
            )
            return

        # Отправляем сообщение с тарифами
        await message.answer(
            "🎁 <b>Выберите тариф подписки:</b>\n\n"
            "1️⃣ 1 месяц - доступ ко всем функциям\n"
            "2️⃣ 3 месяца - скидка 17%\n"
            "3️⃣ 12 месяцев - скидка 33%\n\n"
            "После оплаты отправьте чек администратору в личные сообщения",
            reply_markup=get_subscription_keyboard(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error in cmd_buy: {e}")
        await message.answer("Произошла ошибка при обработке команды")

@router.callback_query(lambda c: c.data.startswith('buy_sub_'))
async def process_buy_subscription(callback: CallbackQuery, session: AsyncSession):
    """Обработчик выбора тарифа подписки"""
    try:
        months = int(callback.data.split('_')[2])
        price = SUBSCRIPTION_PRICES[months]
        
        # Формируем сообщение с реквизитами
        payment_message = (
            f"💳 <b>Оплата подписки на {months} месяц(ев)</b>\n\n"
            f"Сумма к оплате: {price}₽\n\n"
            "Реквизиты для оплаты:\n"
            f"Карта: {PAYMENT_CARD}\n"
            f"Получатель: {PAYMENT_RECEIVER}\n\n"
            "После оплаты:\n"
            "1. Сделайте скриншот чека\n"
            "2. Отправьте его администратору в личные сообщения\n"
            f"3. Укажите ваш ID: {callback.from_user.id}\n\n"
            "После проверки платежа подписка будет активирована в течение 24 часов"
        )

        await callback.message.edit_text(
            text=payment_message,
            parse_mode="HTML"
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in process_buy_subscription: {e}")
        await callback.answer("Произошла ошибка при обработке платежа") 