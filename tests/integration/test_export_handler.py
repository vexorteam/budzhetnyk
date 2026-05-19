from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.handlers.export import handle_export
from src.db.models import Category, Expense
from src.db.repositories.category_repo import CategoryRepository
from src.db.repositories.user_repo import UserRepository


async def _setup_db(db_factory):
    async with db_factory() as session:
        await CategoryRepository(session).seed_system_categories_if_empty()
        user, _ = await UserRepository(session).get_or_create(
            telegram_id=700001, username="exporttest"
        )
        await session.commit()
        return user


async def _add_expense(db_factory, user_id: int, amount: float, created_at: datetime):
    from sqlalchemy import select

    async with db_factory() as session:
        result = await session.execute(
            Category.__table__.select().where(
                Category.system_code == "food", Category.user_id.is_(None)
            )
        )
        cat = result.fetchone()
        expense = Expense(
            user_id=user_id,
            category_id=cat.id,
            amount=Decimal(str(amount)),
            description="тест",
            created_at=created_at,
        )
        session.add(expense)
        await session.commit()


def _make_command(args: str | None) -> MagicMock:
    cmd = MagicMock()
    cmd.args = args
    return cmd


async def test_export_no_data_returns_friendly_message(db_factory):
    user = await _setup_db(db_factory)
    message = AsyncMock()

    with patch("src.bot.handlers.export.get_session_factory", return_value=db_factory):
        with patch(
            "src.bot.handlers.export.datetime"
        ) as mock_dt:
            mock_now = MagicMock()
            mock_now.year = 2026
            mock_now.month = 5
            mock_dt.now.return_value = mock_now
            await handle_export(message, user, _make_command(None))

    message.answer.assert_called_once()
    reply = message.answer.call_args[0][0]
    assert "Немає даних" in reply


async def test_export_invalid_format_returns_error(db_factory):
    user = await _setup_db(db_factory)
    message = AsyncMock()

    with patch("src.bot.handlers.export.get_session_factory", return_value=db_factory):
        await handle_export(message, user, _make_command("not-valid"))

    message.answer.assert_called_once()
    reply = message.answer.call_args[0][0]
    assert "Невірний формат" in reply


async def test_export_specific_month_sends_document(db_factory):
    user = await _setup_db(db_factory)
    await _add_expense(db_factory, user.id, 250.0, datetime(2026, 3, 10))

    message = AsyncMock()

    with patch("src.bot.handlers.export.get_session_factory", return_value=db_factory):
        await handle_export(message, user, _make_command("2026-03"))

    message.answer_document.assert_called_once()
    kwargs = message.answer_document.call_args
    doc = kwargs[0][0]
    assert doc.filename == "expenses_2026-03.xlsx"
    assert "2026-03" in kwargs[1].get("caption", "") or "2026-03" in str(kwargs)


async def test_export_specific_month_no_data(db_factory):
    user = await _setup_db(db_factory)
    message = AsyncMock()

    with patch("src.bot.handlers.export.get_session_factory", return_value=db_factory):
        await handle_export(message, user, _make_command("2099-01"))

    message.answer.assert_called_once()
    reply = message.answer.call_args[0][0]
    assert "Немає даних" in reply
    assert "2099-01" in reply


async def test_export_invalid_month_value(db_factory):
    user = await _setup_db(db_factory)
    message = AsyncMock()

    with patch("src.bot.handlers.export.get_session_factory", return_value=db_factory):
        await handle_export(message, user, _make_command("2026-13"))

    message.answer.assert_called_once()
    reply = message.answer.call_args[0][0]
    assert "Невірний формат" in reply
