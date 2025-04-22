from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from models import User, InviteLink, Subscription, Invite
from db import get_user_by_id
from utils.subscription_manager import create_subscription
import os
import logging
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)
router = Router()

ADMIN_IDS = list(map(int, os.getenv("ADMIN_ID", "").split(",")))
CHAT_ID = int(os.getenv("CHAT_ID", "0"))

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def get_user_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру с действиями для пользователя"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="❌ Удалить пользователя",
                callback_data=f"delete_user_{user_id}"
            ),
            InlineKeyboardButton(
                text="🎁 Выдать подписку",
                callback_data=f"give_sub_{user_id}"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession):
    """Обработчик команды /admin"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ У вас нет доступа к админ-панели.")
        return

    try:
        # Формируем сообщение со списком админских команд
        admin_commands = (
            "👨‍💼 <b>Доступные команды администратора:</b>\n\n"
            "📊 <code>/admin_stats</code> - Показать статистику бота\n"
            "📢 <code>/admin_broadcast</code> - Сделать рассылку\n"
            "👥 <code>/admin_users</code> - Управление пользователями\n\n"
            "ℹ️ Эти команды доступны только администраторам"
        )

        await message.answer(admin_commands, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка при обработке команды admin: {e}")
        await message.answer("❌ Произошла ошибка при получении списка команд.")

@router.callback_query(lambda c: c.data.startswith('delete_user_'))
async def process_delete_user(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """Обработка удаления пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ У вас нет доступа к этой функции")
        return

    try:
        user_id = int(callback.data.split('_')[2])
        user = await get_user_by_id(session, user_id)
        
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        logger.info(f"Начало процесса удаления пользователя {user.telegram_id} из канала {CHAT_ID}")
        
        # Проверяем, что CHAT_ID установлен корректно
        if CHAT_ID == 0:
            logger.error("CHAT_ID не настроен в .env файле")
            await callback.answer("⚠️ Ошибка конфигурации: CHAT_ID не настроен")
            return

        try:
            # Проверяем права бота в канале
            bot_member = await bot.get_chat_member(CHAT_ID, (await bot.me()).id)
            if not bot_member.can_restrict_members:
                logger.error(f"У бота нет прав на удаление участников в канале {CHAT_ID}")
                await callback.answer("⚠️ У бота нет прав администратора в канале")
                return

            # Проверяем, является ли пользователь участником канала
            try:
                member = await bot.get_chat_member(CHAT_ID, user.telegram_id)
                if member:
                    # Удаляем пользователя из канала
                    await bot.ban_chat_member(
                        chat_id=CHAT_ID,
                        user_id=user.telegram_id,
                        revoke_messages=False
                    )
                    logger.info(f"Пользователь {user.telegram_id} успешно удален из канала {CHAT_ID}")
                    
                    # Разбаниваем пользователя, чтобы он мог вернуться с новой подпиской
                    await bot.unban_chat_member(
                        chat_id=CHAT_ID,
                        user_id=user.telegram_id
                    )
                    logger.info(f"Пользователь {user.telegram_id} разбанен в канале {CHAT_ID}")
            except TelegramBadRequest:
                logger.info(f"Пользователь {user.telegram_id} не является участником канала {CHAT_ID}")

            # Удаляем пользователя из базы данных
            await session.delete(user)
            await session.commit()
            logger.info(f"Пользователь {user.telegram_id} удален из базы данных")
            
            # Отправляем уведомление пользователю
            try:
                await bot.send_message(
                    user.telegram_id,
                    "⚠️ Ваш аккаунт был удален администратором.\n"
                    "Вы были удалены из канала."
                )
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление пользователю {user.telegram_id}: {e}")

            await callback.answer("✅ Пользователь успешно удален из базы и канала")
            await callback.message.edit_text(
                f"❌ Пользователь {user.full_name} был удален из базы и канала",
                reply_markup=None
            )

        except TelegramForbiddenError:
            logger.error(f"Бот не имеет доступа к каналу {CHAT_ID}")
            await callback.answer("⚠️ Бот не имеет доступа к каналу")
        except Exception as e:
            logger.error(f"Ошибка при удалении из канала: {e}")
            await callback.answer("⚠️ Ошибка при удалении из канала")
            # Все равно удаляем из базы
            await session.delete(user)
            await session.commit()
            await callback.message.edit_text(
                f"⚠️ Пользователь {user.full_name} удален из базы, но возникла ошибка при удалении из канала",
                reply_markup=None
            )
    
    except Exception as e:
        logger.error(f"Ошибка при удалении пользователя: {e}")
        await callback.answer("❌ Произошла ошибка при удалении пользователя")

@router.callback_query(lambda c: c.data.startswith('give_sub_'))
async def process_give_subscription(callback: CallbackQuery, session: AsyncSession):
    """Обработка выдачи подписки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ У вас нет доступа к этой функции")
        return

    try:
        user_id = int(callback.data.split('_')[2])
        user = await get_user_by_id(session, user_id)
        
        if user:
            # Создаем новую подписку на 30 дней
            subscription = Subscription(
                user_id=user.id,
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(days=30),
                is_active=True,
                auto_renewal=False
            )
            
            # Добавляем подписку в сессию
            session.add(subscription)
            await session.commit()
            
            await callback.answer("✅ Подписка успешно выдана")
            await callback.message.edit_text(
                f"🎁 Пользователю {user.full_name} выдана подписка на 30 дней",
                reply_markup=None
            )
        else:
            await callback.answer("❌ Пользователь не найден")
    
    except Exception as e:
        logger.error(f"Ошибка при выдаче подписки: {e}")
        await callback.answer("❌ Произошла ошибка при выдаче подписки")

@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession):
    """Показывает статистику бота"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ У вас нет доступа к этой функции")
        return

    try:
        # Получаем общее количество пользователей
        users_query = select(User)
        users_result = await session.execute(users_query)
        users = users_result.scalars().all()
        total_users = len(users)

        # Получаем количество активных подписок
        active_subs = sum(1 for user in users if user.is_subscribed)

        # Получаем количество пользователей за последние 24 часа
        day_ago = datetime.now() - timedelta(days=1)
        new_users = sum(1 for user in users if user.created_at >= day_ago)

        # Получаем количество выданных инвайт-ссылок
        invites_query = select(InviteLink)
        invites_result = await session.execute(invites_query)
        invites = invites_result.scalars().all()
        total_invites = len(invites)
        used_invites = sum(1 for invite in invites if invite.is_used)

        # Вычисляем конверсию
        sub_conversion = (active_subs / total_users * 100) if total_users > 0 else 0
        invite_conversion = (used_invites / total_invites * 100) if total_invites > 0 else 0

        stats_message = (
            "📊 <b>Статистика бота:</b>\n\n"
            f"👥 Всего пользователей: {total_users}\n"
            f"📈 Новых за 24 часа: {new_users}\n"
            f"✨ Активных подписок: {active_subs}\n"
            f"🔗 Выдано инвайт-ссылок: {total_invites}\n"
            f"✅ Использовано ссылок: {used_invites}\n\n"
            "💫 <b>Конверсия:</b>\n"
            f"• Подписок: {sub_conversion:.1f}%\n"
            f"• Использования ссылок: {invite_conversion:.1f}%"
        )

        await message.answer(stats_message, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await message.answer("❌ Произошла ошибка при получении статистики")

@router.message(Command("admin_stats"))
async def cmd_admin_stats(message: Message, session: AsyncSession):
    """Обработчик команды /admin_stats"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ У вас нет доступа к админ-панели.")
        return

    try:
        # Получаем всех пользователей с их подписками
        users_query = select(User).options(joinedload(User.subscriptions))
        users_result = await session.execute(users_query)
        users = users_result.unique().scalars().all()

        # Получаем все инвайты
        invites_query = select(Invite)
        invites_result = await session.execute(invites_query)
        invites = invites_result.scalars().all()

        # Получаем все инвайт-ссылки
        invite_links_query = select(InviteLink)
        invite_links_result = await session.execute(invite_links_query)
        invite_links = invite_links_result.scalars().all()

        # Подсчитываем статистику
        total_users = len(users)
        active_subscriptions = sum(1 for user in users if user.is_subscribed)
        total_invites = len(invites)
        used_invites = sum(1 for invite in invites if invite.used_by_id is not None)
        total_invite_links = len(invite_links)
        used_invite_links = sum(1 for link in invite_links if link.is_used)
        
        # Подсчитываем новых пользователей за последние 24 часа
        now = datetime.now()
        new_users_24h = sum(1 for user in users if (now - user.created_at).total_seconds() <= 86400)

        # Формируем сообщение со статистикой
        stats_message = (
            "📊 <b>Общая статистика бота:</b>\n\n"
            f"👥 Всего пользователей: {total_users}\n"
            f"✨ Новых за 24 часа: {new_users_24h}\n"
            f"💫 Активных подписок: {active_subscriptions}\n"
            f"📨 Всего инвайтов: {total_invites}\n"
            f"✅ Использованных инвайтов: {used_invites}\n"
            f"🔗 Выдано инвайт-ссылок: {total_invite_links}\n"
            f"✅ Использовано ссылок: {used_invite_links}\n\n"
            f"📈 Конверсия инвайтов: {round((used_invites / total_invites * 100) if total_invites > 0 else 0, 2)}%\n"
            f"📈 Конверсия ссылок: {round((used_invite_links / total_invite_links * 100) if total_invite_links > 0 else 0, 2)}%\n\n"
            "<b>Статистика по подпискам:</b>\n"
        )

        # Добавляем информацию о подписках
        for user in users:
            # Получаем активную подписку пользователя
            active_subscription = next((sub for sub in user.subscriptions if sub.is_active), None)
            
            if active_subscription:
                sub_info = (
                    f"👤 Пользователь: {user.full_name}\n"
                    f"📅 Начало: {active_subscription.start_date.strftime('%d.%m.%Y')}\n"
                    f"📅 Окончание: {active_subscription.end_date.strftime('%d.%m.%Y')}\n"
                    f"💫 Автопродление: {'✅ Да' if active_subscription.auto_renewal else '❌ Нет'}\n"
                    "➖➖➖➖➖➖➖➖➖➖\n"
                )
                
                # Проверяем, не превысит ли сообщение лимит
                if len(stats_message + sub_info) > 4096:
                    await message.answer(stats_message, parse_mode="HTML")
                    stats_message = sub_info
                else:
                    stats_message += sub_info

        # Отправляем оставшуюся информацию
        if stats_message:
            await message.answer(stats_message, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка при обработке команды admin_stats: {e}")
        await message.answer("❌ Произошла ошибка при получении статистики.")

@router.message(Command("admin_broadcast"))
async def cmd_admin_broadcast(message: Message, session: AsyncSession):
    """Обработчик команды /admin_broadcast"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ У вас нет доступа к админ-панели.")
        return

    try:
        # Получаем всех пользователей
        users_query = select(User)
        result = await session.execute(users_query)
        users = result.scalars().all()

        if not users:
            await message.answer("❌ В базе данных нет пользователей.")
            return

        # Извлекаем текст сообщения (убираем команду)
        broadcast_text = message.text.split(maxsplit=1)[1]
        
        # Отправляем сообщение о начале рассылки
        await message.answer(
            f"📢 Начинаю рассылку сообщения:\n\n"
            f"{broadcast_text}\n\n"
            f"👥 Всего получателей: {len(users)}\n"
            "⏳ Пожалуйста, подождите..."
        )

        # Отправляем сообщения пользователям
        success_count = 0
        error_count = 0
        for user in users:
            try:
                await message.bot.send_message(
                    user.telegram_id,
                    broadcast_text,
                    parse_mode="HTML"
                )
                success_count += 1
                # Добавляем небольшую задержку, чтобы не перегружать API
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения пользователю {user.telegram_id}: {e}")
                error_count += 1

        # Отправляем итоговую статистику
        await message.answer(
            "📊 <b>Рассылка завершена:</b>\n\n"
            f"✅ Успешно отправлено: {success_count}\n"
            f"❌ Ошибок: {error_count}\n"
            f"📈 Успешность: {round((success_count / len(users) * 100), 2)}%"
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке команды admin_broadcast: {e}")
        await message.answer("❌ Произошла ошибка при выполнении рассылки.")

@router.message(Command("admin_users"))
async def cmd_admin_users(message: Message, session: AsyncSession):
    """Обработчик команды /admin_users"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ У вас нет доступа к админ-панели.")
        return

    try:
        # Получаем всех пользователей с их подписками
        query = select(User).options(joinedload(User.subscriptions))
        result = await session.execute(query)
        users = result.unique().scalars().all()
        
        if not users:
            await message.answer("📊 <b>Статистика:</b>\n\n❌ Пользователей не найдено", parse_mode="HTML")
            return

        # Формируем сообщение со статистикой
        stats_message = (
            "📊 <b>Статистика бота:</b>\n\n"
            f"👥 Всего пользователей: {len(users)}\n"
            f"✨ Активных подписок: {sum(1 for user in users if user.is_subscribed)}\n\n"
            "👤 <b>Список пользователей:</b>\n"
            "➖➖➖➖➖➖➖➖➖➖\n\n"
        )

        # Добавляем информацию о каждом пользователе
        for user in users:
            # Получаем активную подписку пользователя
            active_subscription = next((sub for sub in user.subscriptions if sub.is_active), None)

            user_info = (
                f"🆔 <code>{user.telegram_id}</code>\n"
                f"👤 {user.full_name}\n"
                f"📧 {user.email}\n"
                f"☎️ {user.phone}\n"
                f"💫 Подписка: {'✅ Активна' if active_subscription else '❌ Неактивна'}\n"
                "➖➖➖➖➖➖➖➖➖➖\n"
            )
            
            # Проверяем, не превысит ли сообщение лимит
            if len(stats_message + user_info) > 4096:
                await message.answer(stats_message, parse_mode="HTML")
                stats_message = user_info
            else:
                stats_message += user_info

            # Отправляем кнопки действий для каждого пользователя
            await message.answer(
                f"Действия для пользователя {user.full_name}:",
                reply_markup=get_user_actions_keyboard(user.id)
            )

        # Отправляем оставшуюся информацию
        if stats_message:
            await message.answer(stats_message, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка при обработке команды admin_users: {e}")
        await message.answer("❌ Произошла ошибка при получении списка пользователей.")