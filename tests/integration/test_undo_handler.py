from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from src.bot.handlers.undo import UndoCallback, handle_undo, handle_undo_callback
from src.db.repositories.category_repo import CategoryRepository
from src.db.repositories.expense_repo import ExpenseRepository
from src.db.repositories.user_repo import UserRepository
from src.exceptions import NoExpenseToUndoError


async def _setup_db(db_factory, telegram_id: int = 900001):
    async with db_factory() as session:
        cat_repo = CategoryRepository(session)
        await cat_repo.seed_system_categories_if_empty()
        user_repo = UserRepository(session)
        user, _ = await user_repo.get_or_create(telegram_id=telegram_id, username="undouser")
        await session.commit()
        return user


async def _add_expense(db_factory, user_id: int, amount: str, description: str | None = "Кава"):
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


async def test_undo_no_expenses_raises(db_factory):
    user = await _setup_db(db_factory, telegram_id=900001)
    message = AsyncMock()
    message.text = "/undo"

    with patch("src.bot.handlers.undo.get_session_factory", return_value=db_factory):
        with pytest.raises(NoExpenseToUndoError):
            await handle_undo(message, user)


async def test_undo_shows_last_expense(db_factory):
    user = await _setup_db(db_factory, telegram_id=900002)
    await _add_expense(db_factory, user.id, "150", "Обід")

    message = AsyncMock()
    message.text = "/undo"

    with patch("src.bot.handlers.undo.get_session_factory", return_value=db_factory):
        await handle_undo(message, user)

    message.answer.assert_called_once()
    call = message.answer.call_args
    reply = call[0][0]
    assert "150 грн" in reply
    assert "Обід" in reply
    assert "🗑" in reply
    keyboard = call.kwargs.get("reply_markup")
    assert keyboard is not None
    buttons = keyboard.inline_keyboard[0]
    assert len(buttons) == 2
    assert "видалити" in buttons[0].text.lower()
    assert "скасувати" in buttons[1].text.lower()


async def test_undo_confirm_deletes_expense(db_factory):
    user = await _setup_db(db_factory, telegram_id=900003)
    expense_id = await _add_expense(db_factory, user.id, "200", "Піца")

    callback = AsyncMock()
    callback.message = AsyncMock()
    callback_data = UndoCallback(action="confirm", expense_id=expense_id)

    with patch("src.bot.handlers.undo.get_session_factory", return_value=db_factory):
        await handle_undo_callback(callback, callback_data, user)

    callback.message.edit_text.assert_called_once()
    reply = callback.message.edit_text.call_args[0][0]
    assert "✅" in reply
    assert "Видалено" in reply

    async with db_factory() as session:
        repo = ExpenseRepository(session)
        last = await repo.get_last_for_user(user.id)
    assert last is None


async def test_undo_cancel_keeps_expense(db_factory):
    user = await _setup_db(db_factory, telegram_id=900004)
    expense_id = await _add_expense(db_factory, user.id, "300", "Таксі")

    callback = AsyncMock()
    callback.message = AsyncMock()
    callback_data = UndoCallback(action="cancel", expense_id=expense_id)

    with patch("src.bot.handlers.undo.get_session_factory", return_value=db_factory):
        await handle_undo_callback(callback, callback_data, user)

    callback.message.edit_text.assert_called_once()
    reply = callback.message.edit_text.call_args[0][0]
    assert "Скасовано" in reply

    async with db_factory() as session:
        repo = ExpenseRepository(session)
        last = await repo.get_last_for_user(user.id)
    assert last is not None
    assert last.id == expense_id
