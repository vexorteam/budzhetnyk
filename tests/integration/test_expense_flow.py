from decimal import Decimal
from unittest.mock import AsyncMock, patch

from src.bot.handlers.expense import handle_expense
from src.db.repositories.category_repo import CategoryRepository
from src.db.repositories.expense_repo import ExpenseRepository
from src.db.repositories.user_repo import UserRepository


async def _setup_db(db_factory):
    async with db_factory() as session:
        cat_repo = CategoryRepository(session)
        await cat_repo.seed_system_categories_if_empty()
        user_repo = UserRepository(session)
        user, _ = await user_repo.get_or_create(telegram_id=600001, username="tester")
        await session.commit()
        return user


async def test_expense_saved_with_auto_category(db_factory):
    user = await _setup_db(db_factory)

    message = AsyncMock()
    message.text = "Кава 50"

    with patch("src.bot.handlers.expense.get_session_factory", return_value=db_factory):
        await handle_expense(message, user)

    async with db_factory() as session:
        repo = ExpenseRepository(session)
        expense = await repo.get_last_for_user(user.id)

    assert expense is not None
    assert expense.amount == Decimal("50")
    assert expense.description == "Кава"

    message.answer.assert_called_once()
    reply = message.answer.call_args[0][0]
    assert "50 грн" in reply
    assert "🍔" in reply
    assert "Їжа" in reply


async def test_parse_error_replies_with_hint(db_factory):
    user = await _setup_db(db_factory)

    message = AsyncMock()
    message.text = "просто текст без числа"

    with patch("src.bot.handlers.expense.get_session_factory", return_value=db_factory):
        await handle_expense(message, user)

    async with db_factory() as session:
        repo = ExpenseRepository(session)
        expense = await repo.get_last_for_user(user.id)

    assert expense is None
    message.answer.assert_called_once()
    assert "Кава 50" in message.answer.call_args[0][0]


async def test_unknown_category_replies_without_saving(db_factory):
    user = await _setup_db(db_factory)

    message = AsyncMock()
    message.text = "Абажур 300"

    with patch("src.bot.handlers.expense.get_session_factory", return_value=db_factory):
        await handle_expense(message, user)

    async with db_factory() as session:
        repo = ExpenseRepository(session)
        expense = await repo.get_last_for_user(user.id)

    assert expense is None
    message.answer.assert_called_once()
    assert "категорі" in message.answer.call_args[0][0].lower()
