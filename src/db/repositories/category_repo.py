import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Category
from src.utils.constants import DEFAULT_CATEGORIES


class CategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_system_categories(self) -> list[Category]:
        result = await self._session.execute(
            select(Category).where(Category.user_id.is_(None))
        )
        return list(result.scalars().all())

    async def get_user_categories(self, user_id: int) -> list[Category]:
        result = await self._session.execute(
            select(Category).where(Category.user_id == user_id)
        )
        return list(result.scalars().all())

    async def seed_system_categories_if_empty(self) -> None:
        existing = await self.get_system_categories()
        if existing:
            return
        for cat_data in DEFAULT_CATEGORIES:
            category = Category(
                user_id=None,
                name=cat_data["name"],
                emoji=cat_data["emoji"],
                system_code=cat_data["system_code"],
                keywords=json.dumps(cat_data["keywords"], ensure_ascii=False),
            )
            self._session.add(category)
        await self._session.flush()
