from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import ADMIN_IDS
from database import get_all_users, get_user, get_subscription
from datetime import datetime
from aiogram.fsm.context import FSMContext

router = Router()

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔️ Доступ запрещён. Только для администраторов.")
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
             InlineKeyboardButton(text="📋 Пользователи", callback_data="admin_users")],
            [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="🔑 Активировать подписку", callback_data="admin_activate_sub")],
        ]
    )
    await message.answer(
        "<b>👨‍💼 Панель администратора</b>\n\n"
        "Выберите действие:",
        reply_markup=kb
    )

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    users = await get_all_users()
    total = len(users)
    active = 0
    for u in users:
        sub = await get_subscription(u[0])
        if sub:
            end = datetime.strptime(sub[3], "%d.%m.%Y")
            if (end - datetime.now()).days > 0:
                active += 1
    await callback.message.answer(
        f"<b>📊 Статистика бота</b>\n\n"
        f"👥 Всего пользователей: <b>{total}</b>\n"
        f"✅ Активных подписок: <b>{active}</b>\n"
        f"❌ Без подписки: <b>{total - active}</b>\n\n"
        f"🕒 Последнее обновление: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_users")
async def cb_admin_users(callback: CallbackQuery):
    users = await get_all_users()
    if not users:
        await callback.message.answer("❗️ Нет зарегистрированных пользователей.")
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"👤 {u[2]} ({u[1]})", callback_data=f"admin_user_{u[1]}")] for u in users
        ]
    )
    await callback.message.answer("<b>📋 Список пользователей:</b>", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("admin_user_"))
async def admin_user_info(callback: CallbackQuery):
    tg_id = int(callback.data.split("_")[-1])
    user = await get_user(tg_id)
    if not user:
        await callback.message.answer("Пользователь не найден.")
        return
    sub = await get_subscription(user[0])
    sub_status = "❌ Неактивна"
    days_left = 0
    if sub:
        sub_status = "✅ Активна"
        end = datetime.strptime(sub[3], "%d.%m.%Y")
        days_left = (end - datetime.now()).days
        if days_left < 0:
            days_left = 0
    await callback.message.answer(
        f"<b>🗂️ Информация о пользователе</b>\n"
        f"<b>ID:</b> <code>{user[1]}</code>\n"
        f"<b>👤 Имя:</b> {user[2]}\n"
        f"<b>📧 Email:</b> {user[4]}\n"
        f"<b>📱 Телефон:</b> {user[3]}\n\n"
        f"<b>🟢 Статус подписки:</b> {sub_status}\n"
        f"{'⏳ Дней осталось: ' + str(days_left) if sub else ''}"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("✍️ Введите текст для рассылки всем пользователям одним сообщением.\n\n<code>/send Текст рассылки</code>")
    await callback.answer()

@router.message(Command("send"))
async def cmd_send_broadcast(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔️ Доступ запрещён.")
        return
    text = message.text.partition(' ')[2].strip()
    if not text:
        await message.answer("Введите текст для рассылки после команды.\nПример: /send Ваш текст")
        return
    users = await get_all_users()
    sent = 0
    for u in users:
        try:
            await message.bot.send_message(u[1], text)
            sent += 1
        except Exception:
            pass
    await message.answer(f"📢 Рассылка завершена. Сообщение отправлено {sent} пользователям.")

@router.callback_query(F.data == "admin_activate_sub")
async def cb_admin_activate_sub(callback: CallbackQuery):
    await callback.message.answer("🔑 Для активации подписки отправьте команду в формате:\n<code>/activate_sub user_id months</code>\n\nПример: /activate_sub 123456789 3")
    await callback.answer()

@router.message(Command("activate_sub"))
async def cmd_activate_sub(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔️ Доступ запрещён.")
        return
    args = message.text.split()
    if len(args) != 3:
        await message.answer("Использование: /activate_sub user_id months\nПример: /activate_sub 123456789 3")
        return
    try:
        tg_id = int(args[1])
        months = int(args[2])
    except ValueError:
        await message.answer("user_id и months должны быть числами.")
        return
    user = await get_user(tg_id)
    if not user:
        await message.answer("Пользователь не найден.")
        return
    from database import deactivate_subscriptions, add_subscription
    from datetime import datetime, timedelta
    await deactivate_subscriptions(user[0])
    start = datetime.now()
    end = start + timedelta(days=30*months)
    await add_subscription(user[0], start.strftime("%d.%m.%Y"), end.strftime("%d.%m.%Y"))
    await message.answer(f"✅ Подписка активирована для пользователя <b>{user[2]}</b> (<code>{tg_id}</code>) на <b>{months}</b> мес.")
    try:
        await message.bot.send_message(tg_id, f"🎉 Ваша подписка активирована до {end.strftime('%d.%m.%Y')}! Спасибо за оплату.")
    except Exception:
        pass 