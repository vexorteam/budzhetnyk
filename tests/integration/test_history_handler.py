from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from src.bot.handlers.history import handle_history
from src.db.repositories.category_repo import CategoryRepository
from src.db.repositories.expense_repo import ExpenseRepository
from src.db.repositories.user_repo import UserRepository


async def _setup_db(db_factory, telegram_id: int = 910001):
    async with db_factory() as session:
        cat_repo = CategoryRepository(session)
        await cat_repo.seed_system_categories_if_empty()
        user_repo = UserRepository(session)
        user, _ = await user_repo.get_or_create(telegram_id=telegram_id, username="histuser")
        await session.commit()
        return user


async def _add_expense(db_factory, user_id: int, amount: str, description: str | None):
    async with db_factory() as session:
        cat_repo = CategoryRepository(session)
        cats = await cat_repo.get_system_categories()
        food_cat = next(c for c in cats if c.system_code == "food")
        repo = ExpenseRepository(session)
        expense = await repo.create(
            user_id=user_id,
            category_id=food_cat.id,
            amount=Decimal(amount),
            description=description,
        )
        await session.commit()
        return expense.id


async def test_history_no_expenses(db_factory):
    user = await _setup_db(db_factory, telegram_id=910001)
    message = AsyncMock()

    with patch("src.bot.handlers.history.get_session_factory", return_value=db_factory):
        await handle_history(message, user)

    message.answer.assert_called_once()
    reply = message.answer.call_args[0][0]
    assert "немає" in reply.lower()


async def test_history_shows_expenses(db_factory):
    user = await _setup_db(db_factory, telegram_id=910002)
    await _add_expense(db_factory, user.id, "50", "Кава")
    await _add_expense(db_factory, user.id, "120", "Обід")

    message = AsyncMock()

    with patch("src.bot.handlers.history.get_session_factory", return_value=db_factory):
        await handle_history(message, user)

    message.answer.assert_called_once()
    reply = message.answer.call_args[0][0]
    assert "50 грн" in reply
    assert "120 грн" in reply
    assert "Кава" in reply
    assert "Обід" in reply
    assert "📋" in reply


async def test_history_shows_at_most_10(db_factory):
    user = await _setup_db(db_factory, telegram_id=910003)
    for i in range(15):
        await _add_expense(db_factory, user.id, str(10 + i), f"Витрата {i}")

    message = AsyncMock()

    with patch("src.bot.handlers.history.get_session_factory", return_value=db_factory):
        await handle_history(message, user)

    reply = message.answer.call_args[0][0]
    lines = [ln for ln in reply.split("\n") if ln.strip() and "📋" not in ln]
    assert len(lines) == 10


async def test_history_newest_first(db_factory):
    user = await _setup_db(db_factory, telegram_id=910004)
    await _add_expense(db_factory, user.id, "100", "Перша")
    await _add_expense(db_factory, user.id, "200", "Друга")

    message = AsyncMock()

    with patch("src.bot.handlers.history.get_session_factory", return_value=db_factory):
        await handle_history(message, user)

    reply = message.answer.call_args[0][0]
    idx_first = reply.index("Перша")
    idx_second = reply.index("Друга")
    assert idx_second < idx_first
