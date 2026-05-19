from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Expense


class ExpenseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: int,
        category_id: int,
        amount: Decimal,
        description: str | None,
    ) -> Expense:
        expense = Expense(
            user_id=user_id,
            category_id=category_id,
            amount=amount,
            description=description,
        )
        self._session.add(expense)
        await self._session.flush()
        return expense

    async def get_last_for_user(self, user_id: int) -> Expense | None:
        result = await self._session.execute(
            select(Expense)
            .where(Expense.user_id == user_id)
            .order_by(Expense.created_at.desc(), Expense.id.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def get_period_expenses(
        self,
        user_id: int,
        date_from: datetime,
        date_to: datetime,
    ) -> list[Expense]:
        result = await self._session.execute(
            select(Expense)
            .where(
                Expense.user_id == user_id,
                Expense.created_at >= date_from,
                Expense.created_at < date_to,
            )
            .order_by(Expense.created_at)
        )
        return list(result.scalars().all())

    async def delete(self, expense_id: int) -> None:
        result = await self._session.execute(select(Expense).where(Expense.id == expense_id))
        expense = result.scalars().first()
        if expense is not None:
            await self._session.delete(expense)
            await self._session.flush()

    async def get_recent(self, user_id: int, limit: int = 10) -> list[Expense]:
        result = await self._session.execute(
            select(Expense)
            .where(Expense.user_id == user_id)
            .order_by(Expense.created_at.desc(), Expense.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_month_total(self, user_id: int, year: int, month: int) -> Decimal:
        date_from = datetime(year, month, 1)
        date_to = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
        result = await self._session.execute(
            select(func.sum(Expense.amount)).where(
                Expense.user_id == user_id,
                Expense.created_at >= date_from,
                Expense.created_at < date_to,
            )
        )
        val = result.scalar()
        return Decimal(str(val)) if val is not None else Decimal("0")
