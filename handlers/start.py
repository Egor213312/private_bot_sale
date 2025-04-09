from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states import Registration
from models import User
from database import async_session
from sqlalchemy import select
from aiogram.filters import Command

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await message.answer("👋 Привет! Давайте зарегистрируемся.\nВведите имя и фамилию:")
    await state.set_state(Registration.full_name)

@router.message(Registration.full_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("Теперь введите ваш email:")
    await state.set_state(Registration.email)

@router.message(Registration.email)
async def process_email(message: Message, state: FSMContext):
    data = await state.get_data()
    full_name = data["full_name"]
    email = message.text
    telegram_id = message.from_user.id

    async with async_session() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.full_name = full_name
            user.email = email
        else:
            user = User(telegram_id=telegram_id, full_name=full_name, email=email)
            session.add(user)

        await session.commit()

    await message.answer("✅ Вы успешно зарегистрированы!\nДля активации используйте /buy")
    await state.clear()

@router.message(Command("info"))
async def cmd_info(message: Message):
    telegram_id = message.from_user.id

    async with async_session() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            status = "✅ Активна" if user.is_subscribed else "❌ Не активна"
            await message.answer(
                f"📄 Ваш профиль:\n"
                f"🆔 ID: <code>{user.telegram_id}</code>\n"
                f"👤 Имя: {user.full_name}\n"
                f"📧 Email: {user.email}\n\n"
                f"📌 Подписка:\n{status}\n"
                f"💳 Для активации используйте /buy"
            )
        else:
            await message.answer("Вы еще не зарегистрированы. Используйте /start.")

@router.message(Command("buy"))
async def cmd_buy(message: Message):
    await message.answer("🛒 Здесь будет покупка подписки (пока не реализовано).")

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    telegram_id = message.from_user.id

    async with async_session() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            await message.answer("👤 Вы уже зарегистрированы!\nПосмотреть профиль — /info")
            return

    await message.answer("👋 Привет! Давайте зарегистрируемся.\nВведите имя и фамилию:")
    await state.set_state(Registration.full_name)
