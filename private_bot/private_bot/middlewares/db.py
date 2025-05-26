from aiogram import BaseMiddleware
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from db import async_session
from typing import Callable, Dict, Any, Awaitable

class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        async with async_session() as session:
            try:
                data["session"] = session
                return await handler(event, data)
            finally:
                await session.close() 