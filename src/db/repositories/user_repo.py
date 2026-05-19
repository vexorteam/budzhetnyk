from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import User
from src.exceptions import DatabaseError, UserNotFoundError


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User:
        result = await self._session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise UserNotFoundError(telegram_id)
        return user

    async def create(self, telegram_id: int, username: str | None = None) -> User:
        user = User(telegram_id=telegram_id, username=username)
        self._session.add(user)
        await self._session.flush()
        return user

    async def get_or_create(
        self, telegram_id: int, username: str | None = None
    ) -> tuple[User, bool]:
        result = await self._session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is not None:
            return user, False
        user = await self.create(telegram_id, username)
        return user, True

    async def set_monthly_limit(self, user_id: int, limit: Decimal | None) -> None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise DatabaseError(f"User id={user_id} not found")
        user.monthly_limit = limit
        await self._session.flush()
