from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.orm import selectinload

from src.db.models import Expense, User
from src.db.session import get_session_factory
from src.utils.formatters import format_expense_line

router = Router(name="history")


@router.message(Command("history"))
async def handle_history(message: Message, user: User) -> None:
    factory = get_session_factory()
    async with factory() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(Expense)
            .options(selectinload(Expense.category))
            .where(Expense.user_id == user.id)
            .order_by(Expense.created_at.desc(), Expense.id.desc())
            .limit(10)
        )
        expenses = list(result.scalars().all())

    if not expenses:
        await message.answer(
            "Витрат ще немає. Додайте першу: наприклад, <code>Кава 50</code>"
        )
        return

    lines = ["📋 <b>Останні витрати:</b>", ""]
    for expense in expenses:
        lines.append(format_expense_line(expense))

    await message.answer("\n".join(lines))
