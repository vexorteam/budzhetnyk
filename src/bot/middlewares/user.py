from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.db.repositories.user_repo import UserRepository
from src.db.session import get_session_factory


class UserMiddleware(BaseMiddleware):
    def __init__(self, session_factory: async_sessionmaker | None = None) -> None:
        self._session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        telegram_user: TelegramUser | None = data.get("event_from_user")
        if telegram_user is not None:
            factory = self._session_factory or get_session_factory()
            async with factory() as session:
                repo = UserRepository(session)
                user, _ = await repo.get_or_create(
                    telegram_id=telegram_user.id,
                    username=telegram_user.username,
                )
                await session.commit()
            data["user"] = user
        return await handler(event, data)
