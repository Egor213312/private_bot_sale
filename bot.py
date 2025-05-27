import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from aiogram.client.bot import DefaultBotProperties 
from database import init_db
from handlers import user, admin

async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(user.router)
    dp.include_router(admin.router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 