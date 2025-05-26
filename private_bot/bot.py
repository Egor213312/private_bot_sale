import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage
from db import engine, create_db, async_session
import os
from dotenv import load_dotenv
from handlers import start, admin, info, invite, subscription
from utils.subscription_checker import start_subscription_checker
from middlewares.db import DatabaseMiddleware
from aiogram.exceptions import TelegramConflictError
import aiohttp
import sys
import time
from aiohttp import web
import ssl
from contextlib import asynccontextmanager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/private_bot.log')
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

# Проверка наличия необходимых переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле")

logger.info(f"Загружен токен бота: {BOT_TOKEN[:5]}...{BOT_TOKEN[-5:]}")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Добавление middleware
dp.update.middleware(DatabaseMiddleware())

@asynccontextmanager
async def get_client_session():
    session = aiohttp.ClientSession()
    try:
        yield session
    finally:
        await session.close()

async def delete_webhook():
    try:
        webhook_info = await bot.get_webhook_info()
        logger.info(f"Текущая информация о webhook: {webhook_info}")
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook успешно удален")
        webhook_info = await bot.get_webhook_info()
        logger.info(f"Информация о webhook после удаления: {webhook_info}")
    except Exception as e:
        logger.error(f"Ошибка при удалении webhook: {e}")
        raise

async def setup_webhook():
    try:
        await delete_webhook()
        async with get_client_session() as session:
            async with session.get('https://api.ipify.org?format=json') as response:
                ip_data = await response.json()
                server_ip = ip_data['ip']
        webhook_url = f"https://{server_ip}:8443/webhook"
        logger.info(f"Настройка webhook на URL: {webhook_url}")
        certificate = FSInputFile('/root/private_bot/certs/cert.pem')
        await bot.set_webhook(
            url=webhook_url,
            certificate=certificate,
            drop_pending_updates=True
        )
        logger.info("Webhook успешно установлен")
        webhook_info = await bot.get_webhook_info()
        logger.info(f"Информация о webhook после установки: {webhook_info}")
        return webhook_url
    except Exception as e:
        logger.error(f"Ошибка при настройке webhook: {e}")
        raise

async def webhook_handler(request):
    try:
        update = await request.json()
        logger.info(f"Получено обновление: {update}")
        await dp.feed_webhook_update(bot, update)
        return web.Response()
    except Exception as e:
        logger.error(f"Ошибка при обработке webhook: {e}")
        return web.Response(status=500)

async def setup_bot():
    try:
        bot_info = await bot.get_me()
        logger.info(f"Информация о боте: {bot_info}")
        await create_db()
        logger.info("База данных успешно инициализирована")
        dp.include_router(start.router)
        dp.include_router(admin.router)
        dp.include_router(info.router)
        dp.include_router(invite.router)
        dp.include_router(subscription.router)
        logger.info("Роутеры успешно зарегистрированы")
        await bot.set_my_commands([
            BotCommand(command="start", description="Начать"),
            BotCommand(command="info", description="Профиль"),
            BotCommand(command="subscription", description="Управление подпиской"),
            BotCommand(command="invite", description="Получить инвайт-ссылку")
        ])
        logger.info("Команды бота успешно установлены")
        asyncio.create_task(start_subscription_checker(async_session(), bot))
        logger.info("Фоновая проверка подписок запущена")
    except Exception as e:
        logger.error(f"Ошибка при настройке бота: {e}")
        raise

async def cleanup():
    try:
        await delete_webhook()
        await bot.session.close()
        await engine.dispose()
        logger.info("Ресурсы успешно очищены")
    except Exception as e:
        logger.error(f"Ошибка при очистке ресурсов: {e}")

async def main():
    try:
        logger.info("Начало запуска бота...")
        await setup_bot()
        webhook_url = await setup_webhook()
        app = web.Application()
        app.router.add_post("/webhook", webhook_handler)
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(
            '/root/private_bot/certs/cert.pem',
            '/root/private_bot/certs/private.key'
        )
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8443, ssl_context=ssl_context)
        await site.start()
        logger.info(f"Веб-сервер запущен на порту 8443")
        logger.info(f"Webhook URL: {webhook_url}")
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            logger.info("Получен сигнал завершения работы")
        finally:
            await cleanup()
            await runner.cleanup()
    except Exception as e:
        logger.error(f"Произошла ошибка при запуске бота: {e}")
        await cleanup()
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
