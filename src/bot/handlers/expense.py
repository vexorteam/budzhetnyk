from aiogram import F, Router
from aiogram.types import Message

from src.db.models import User
from src.db.repositories.expense_repo import ExpenseRepository
from src.db.session import get_session_factory
from src.exceptions import ExpenseParsingError
from src.services.categorizer import guess_category
from src.services.parser import parse_expense
from src.utils.formatters import format_amount

router = Router(name="expense")


@router.message(F.text, ~F.text.startswith("/"))
async def handle_expense(message: Message, user: User) -> None:
    text = message.text or ""

    try:
        parsed = parse_expense(text)
    except ExpenseParsingError:
        await message.answer("Не зрозумів 🤔 Спробуйте: <code>Кава 50</code>")
        return

    factory = get_session_factory()
    async with factory() as session:
        category = await guess_category(parsed.description, user.id, session)

        if category is None:
            await message.answer("Не зміг визначити категорію 🤷")
            return

        repo = ExpenseRepository(session)
        await repo.create(
            user_id=user.id,
            category_id=category.id,
            amount=parsed.amount,
            description=parsed.description,
        )
        await session.commit()

    amount_str = format_amount(parsed.amount)
    desc_part = f" · {parsed.description}" if parsed.description else ""
    await message.answer(
        f"✅ Додано: {amount_str} · {category.emoji} {category.name}{desc_part}"
    )
