import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
from db import engine, create_db, async_session
import os
from dotenv import load_dotenv
from handlers import start, admin, info, invite, subscription
from utils.subscription_manager import start_subscription_checker
from middlewares.db import DatabaseMiddleware

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Проверка наличия необходимых переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Добавление middleware
dp.update.middleware(DatabaseMiddleware())

async def main():
    try:
        # Создание базы данных
        await create_db()
        logger.info("База данных успешно инициализирована")

        # Регистрация роутеров
        dp.include_router(start.router)
        dp.include_router(admin.router)
        dp.include_router(info.router)
        dp.include_router(invite.router)
        dp.include_router(subscription.router)
        logger.info("Роутеры успешно зарегистрированы")

        # Установка команд бота
        await bot.set_my_commands([
            BotCommand(command="start", description="Начать"),
            BotCommand(command="info", description="Профиль"),
            BotCommand(command="admin", description="Админ-панель"),
            BotCommand(command="buy", description="Активация подписки"),
            BotCommand(command="subscription", description="Информация о подписке"),
            BotCommand(command="invite", description="Получить инвайт-ссылку"),
        ])
        logger.info("Команды бота успешно установлены")

        # Запуск проверки подписок в фоновом режиме
        asyncio.create_task(start_subscription_checker(async_session(), bot))
        logger.info("Фоновая проверка подписок запущена")

        # Запуск бота
        logger.info("Бот запускается...")
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Произошла ошибка при запуске бота: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
