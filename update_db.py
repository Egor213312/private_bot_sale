import asyncio
from db import engine, async_session
from models import Base

async def update_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("База данных успешно обновлена")

if __name__ == "__main__":
    asyncio.run(update_database()) 