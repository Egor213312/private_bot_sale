from sqlalchemy.ext.asyncio import create_async_engine
from models import Base
import asyncio
import logging

logger = logging.getLogger(__name__)

async def recreate_database():
    """Пересоздает все таблицы в базе данных"""
    try:
        # Получаем параметры подключения из переменных окружения
        import os
        from dotenv import load_dotenv
        load_dotenv()

        DB_HOST = os.getenv("DB_HOST")
        DB_PORT = os.getenv("DB_PORT")
        DB_NAME = os.getenv("DB_NAME")
        DB_USER = os.getenv("DB_USER")
        DB_PASSWORD = os.getenv("DB_PASSWORD")

        # Формируем URL для подключения
        DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

        # Создаем движок
        engine = create_async_engine(DATABASE_URL, echo=True)

        # Удаляем все таблицы
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("Все таблицы успешно удалены")

        # Создаем таблицы заново
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Все таблицы успешно созданы")

    except Exception as e:
        logger.error(f"Ошибка при пересоздании базы данных: {e}")
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(recreate_database()) 