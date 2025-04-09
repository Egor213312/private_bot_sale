import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
from handlers import start, admin
from database import engine
from database_init import init_db
import os
from dotenv import load_dotenv

load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())

async def main():
    await init_db()
    dp.include_router(start.router)
    dp.include_router(admin.router)

    await bot.set_my_commands([
        BotCommand(command="start", description="Начать"),
        BotCommand(command="info", description="Профиль"),
        BotCommand(command="admin", description="Админ-панель"),
        BotCommand(command="buy", description="Активация подписки"),
    ])

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
