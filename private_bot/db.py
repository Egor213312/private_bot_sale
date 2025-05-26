from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from models import Base, User
from dotenv import load_dotenv
import os
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

load_dotenv()

# Получение параметров подключения к БД
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

if not all([DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD]):
    raise ValueError("Не все необходимые переменные окружения для БД найдены")

# Формирование URL для подключения
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

try:
    engine = create_async_engine(DATABASE_URL, echo=True)
    logger.info("Движок базы данных успешно создан")
except Exception as e:
    logger.error(f"Ошибка при создании движка базы данных: {e}")
    raise

async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

async def create_db():
    """Создание всех таблиц в базе данных"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Таблицы базы данных успешно созданы")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц базы данных: {e}")
        raise

async def get_user_by_id(session: AsyncSession, user_id: int) -> User:
    """Получение пользователя по ID"""
    try:
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя {user_id}: {e}")
        return None

async def get_user_by_telegram_id(telegram_id: int, session: AsyncSession) -> User:
    """Получение пользователя по Telegram ID"""
    try:
        query = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            logger.warning(f"Пользователь с telegram_id {telegram_id} не найден")
        return user
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя {telegram_id}: {e}")
        return None

async def create_user(telegram_id: int, full_name: str, email: str, phone: str, session: AsyncSession) -> User:
    """Создание нового пользователя"""
    try:
        # Проверяем, не существует ли уже пользователь с таким telegram_id
        existing_user = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        if existing_user.scalar_one_or_none():
            logger.warning(f"Пользователь с telegram_id {telegram_id} уже существует")
            return None

        # Проверяем, не существует ли уже пользователь с таким email
        existing_email = await session.execute(
            select(User).where(User.email == email.lower().strip())
        )
        if existing_email.scalar_one_or_none():
            logger.warning(f"Пользователь с email {email} уже существует")
            return None

        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            email=email.lower().strip(),
            phone=phone
        )
        session.add(user)
        await session.commit()
        logger.info(f"Пользователь {telegram_id} успешно создан")
        return user
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя {telegram_id}: {e}")
        await session.rollback()
        return None
