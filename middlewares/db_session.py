from typing import Callable, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession
from database.db_helper import db_helper

class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with db_helper.session_factory() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                # Commit any work the handler left uncommitted, then end the
                # transaction so the connection doesn't linger "idle in transaction".
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
