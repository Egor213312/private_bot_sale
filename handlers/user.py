from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_user, add_user, update_user_email, update_user_phone, get_subscription, add_subscription, deactivate_subscriptions, add_invite_link, get_invite_link
from keyboards import main_kb, tariff_kb
from config import ADMIN_IDS, CHANNEL_ID
from datetime import datetime, timedelta

router = Router()

class Registration(StatesGroup):
    waiting_for_phone = State()
    waiting_for_email = State()

@router.message(Command("start"))
async def cmd_start(message: Message):
    text = (
        "👋 Добро пожаловать в бота для продажи подписок на закрытый канал!\n\n"
        "📝 Доступные команды:\n"
        "📋 /registration — регистрация нового пользователя\n"
        "ℹ️ /info — информация о вашем аккаунте\n"
        "💳 /buy — купить подписку\n"
        "📅 /subscription — информация о подписке\n"
        "🔗 /invite — получить инвайт-ссылку в канал\n\n"
        "🚀 Для начала работы, пожалуйста, зарегистрируйтесь с помощью /registration."
    )
    await message.answer(text, reply_markup=main_kb)

@router.message(Command("registration"))
async def cmd_registration(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте ваш номер телефона:")
    await state.set_state(Registration.waiting_for_phone)

@router.message(Registration.waiting_for_phone)
async def reg_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    await state.update_data(phone=phone)
    await message.answer("Теперь, пожалуйста, введите ваш email:")
    await state.set_state(Registration.waiting_for_email)

@router.message(Registration.waiting_for_email)
async def reg_email(message: Message, state: FSMContext):
    email = message.text.strip()
    data = await state.get_data()
    phone = data.get("phone")
    user = await get_user(message.from_user.id)
    if not user:
        await add_user(message.from_user.id, message.from_user.full_name, phone, email)
    else:
        await update_user_phone(message.from_user.id, phone)
        await update_user_email(message.from_user.id, email)
    await message.answer(
        f"✅ Регистрация успешно завершена!\n\n"
        f"📋 <b>Ваши данные:</b>\n"
        f"👤 Имя: {message.from_user.full_name}\n"
        f"📱 Телефон: {phone}\n"
        f"📧 Email: {email}\n\n"
        f"ℹ️ Используйте /info для просмотра информации о себе."
    )
    await state.clear()

@router.message(Command("info"))
async def cmd_info(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Вы не зарегистрированы. Используйте /registration.")
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
    await message.answer(
        f"<b>🗂️ Информация о пользователе</b>\n"
        f"<b>ID:</b> <code>{user[1]}</code>\n"
        f"<b>👤 Имя:</b> {user[2]}\n"
        f"<b>📧 Email:</b> {user[4]}\n"
        f"<b>📱 Телефон:</b> {user[3]}\n\n"
        f"<b>🟢 Статус подписки:</b>\n{sub_status}\n"
        f"{'⏳ Дней осталось: ' + str(days_left) if sub else ''}\n\n"
        f"<b>📌 Доступные команды:</b>\n"
        f"/buy - Купить подписку\n"
        f"/invite - Получить инвайт-ссылку\n"
        f"/info - Информация о профиле"
    )

@router.message(Command("buy"))
async def cmd_buy(message: Message):
    await message.answer(
        "🎁 Выберите тариф подписки:\n\n"
        "1 месяц - доступ ко всем функциям\n"
        "3 месяца - скидка 17%\n"
        "12 месяцев - скидка 33%\n\n"
        "После оплаты отправьте чек администратору в личные сообщения",
        reply_markup=tariff_kb
    )

@router.callback_query(F.data.startswith("tariff_"))
async def process_tariff(callback: CallbackQuery):
    tariff = callback.data.split("_")[1]
    days = {"1": 30, "3": 90, "12": 365}[tariff]
    price = {"1": 200, "3": 500, "12": 1500}[tariff]
    user = await get_user(callback.from_user.id)
    pay_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Оплатил", callback_data=f"paid_{tariff}")]
        ]
    )
    await callback.message.answer(
        f"<b>💳 Оплата подписки на {days // 30} месяц(ев)</b>\n\n"
        f"💰 <b>Сумма к оплате:</b> {price}₽\n\n"
        f"<b>Реквизиты для оплаты:</b>\n"
        f"📱 Номер телефона: 89870812935\n"
        f"💳 Карта: 2202208399336685\n"
        f"👤 Получатель: Егор Ильичев\n\n"
        f"🏦 Сбербанк\n\n"
        f"<b>📝 После оплаты:</b>\n"
        f"1. Сделайте скриншот чека\n"
        f"2. Отправьте его администратору по номеру: 89870812935\n"
        f"3. Укажите ваш ID: <code>{user[1]}</code>\n\n"
        f"⏳ После проверки платежа подписка будет активирована в течение 1 часа",
        reply_markup=pay_kb
    )
    await callback.answer()

@router.callback_query(F.data.startswith("paid_"))
async def paid_callback(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    tariff = callback.data.split("_")[1]
    months = {"1": 1, "3": 3, "12": 12}[tariff]
    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(
                admin_id,
                f"💸 <b>Поступила заявка на оплату!</b>\n\n"
                f"👤 Пользователь: <b>{user[2]}</b>\n"
                f"🆔 ID: <code>{user[1]}</code>\n"
                f"Тариф: {months} мес.\n\n"
                f"Проверьте чек и активируйте подписку командой:\n"
                f"/activate_sub {user[1]} {months}"
            )
        except Exception:
            pass
    await callback.message.answer("Спасибо! Ваша заявка на оплату отправлена администратору. Подписка будет активирована после проверки.")
    await callback.answer()

@router.message(Command("subscription"))
async def cmd_subscription(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Вы не зарегистрированы. Используйте /registration.")
        return
    sub = await get_subscription(user[0])
    if not sub:
        await message.answer("У вас нет активной подписки. Используйте /buy для покупки.")
        return
    end = datetime.strptime(sub[3], "%d.%m.%Y")
    days_left = (end - datetime.now()).days
    await message.answer(
        f"<b>Информация о подписке</b>\n"
        f"✅ Подписка активна\n"
        f"• Дней осталось: {days_left}\n"
        f"• Дата окончания: {sub[3]}\n"
        f"• Автопродление: Отключено\n\n"
        f"• История подписок:\n• {sub[2]} - {sub[3]}"
    )

@router.message(Command("invite"))
async def cmd_invite(message: Message, bot):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Вы не зарегистрированы. Используйте /registration.")
        return
    sub = await get_subscription(user[0])
    if not sub:
        await message.answer("У вас нет активной подписки. Используйте /buy для покупки.")
        return
    # Проверяем, была ли уже выдана ссылка
    invite_link = await get_invite_link(user[0])
    if invite_link:
        await message.answer(
            f"🔗 Ваша одноразовая инвайт-ссылка уже была выдана ранее:\n\n{invite_link}\n\n"
            f"⚠️ Ссылка действительна 24 часа и может быть использована только один раз."
        )
        return
    # Генерация одноразовой ссылки
    invite = await bot.create_chat_invite_link(
        chat_id=CHANNEL_ID,
        expire_date=int((datetime.now() + timedelta(days=1)).timestamp()),
        member_limit=1
    )
    await add_invite_link(user[0], invite.invite_link)
    await message.answer(
        f"🎁 Ваша одноразовая инвайт-ссылка в закрытый канал:\n\n{invite.invite_link}\n\n"
        f"⚠️ Ссылка действительна 24 часа и может быть использована только один раз."
    )

@router.message(lambda m: m.text == "👤 Профиль")
async def profile_btn(message: Message):
    await cmd_info(message)

@router.message(lambda m: m.text == "💳 Купить подписку")
async def buy_btn(message: Message):
    await cmd_buy(message)

@router.message(lambda m: m.text == "📅 Информация о подписке")
async def subinfo_btn(message: Message):
    await cmd_subscription(message)

@router.message(lambda m: m.text == "🔗 Получить ссылку")
async def invite_btn(message: Message, bot):
    await cmd_invite(message, bot) 