"""Integration tests for ErrorMiddleware."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.bot.middlewares.error import ErrorMiddleware, _try_reply
from src.exceptions import (
    DatabaseError,
    NoDataForChartError,
    NoExpenseToUndoError,
)


def _make_update(chat_id: int = 123) -> MagicMock:
    """Create a mock Update with a message in the given chat."""
    from aiogram.types import Update

    update = MagicMock(spec=Update)
    update.message = MagicMock()
    update.message.chat = MagicMock()
    update.message.chat.id = chat_id
    update.callback_query = None
    return update


def _make_data(bot: Any = None) -> dict:
    mock_bot = bot or AsyncMock()
    mock_bot.send_message = AsyncMock()
    return {"bot": mock_bot}


@pytest.mark.asyncio
async def test_domain_error_sends_friendly_message():
    middleware = ErrorMiddleware()

    async def failing_handler(event, data):
        raise NoExpenseToUndoError()

    update = _make_update()
    data = _make_data()

    await middleware(failing_handler, update, data)

    data["bot"].send_message.assert_called_once()
    args = data["bot"].send_message.call_args
    assert args[0][0] == 123
    assert "скасування" in args[0][1].lower() or "витрат" in args[0][1].lower()


@pytest.mark.asyncio
async def test_unknown_error_sends_generic_message():
    middleware = ErrorMiddleware()

    async def failing_handler(event, data):
        raise RuntimeError("unexpected boom")

    update = _make_update()
    data = _make_data()

    await middleware(failing_handler, update, data)

    data["bot"].send_message.assert_called_once()
    args = data["bot"].send_message.call_args[0]
    assert "помилка" in args[1].lower()


@pytest.mark.asyncio
async def test_no_domain_error_passes_through():
    middleware = ErrorMiddleware()
    result_holder = []

    async def ok_handler(event, data):
        result_holder.append("ok")
        return "done"

    update = _make_update()
    data = _make_data()

    result = await middleware(ok_handler, update, data)

    assert result == "done"
    assert result_holder == ["ok"]
    data["bot"].send_message.assert_not_called()


@pytest.mark.asyncio
async def test_no_data_for_chart_error_message():
    middleware = ErrorMiddleware()

    async def failing_handler(event, data):
        raise NoDataForChartError()

    update = _make_update(chat_id=456)
    data = _make_data()

    await middleware(failing_handler, update, data)

    args = data["bot"].send_message.call_args[0]
    assert args[0] == 456
    assert "графіка" in args[1].lower() or "даних" in args[1].lower()


@pytest.mark.asyncio
async def test_database_error_sends_specific_message():
    middleware = ErrorMiddleware()

    async def failing_handler(event, data):
        raise DatabaseError("connection failed")

    update = _make_update()
    data = _make_data()

    await middleware(failing_handler, update, data)

    args = data["bot"].send_message.call_args[0]
    assert "бази даних" in args[1].lower() or "помилка" in args[1].lower()


@pytest.mark.asyncio
async def test_callback_query_event_uses_callback_chat():
    from aiogram.types import Update

    middleware = ErrorMiddleware()

    async def failing_handler(event, data):
        raise NoExpenseToUndoError()

    update = MagicMock(spec=Update)
    update.message = None
    update.callback_query = MagicMock()
    update.callback_query.message = MagicMock()
    update.callback_query.message.chat = MagicMock()
    update.callback_query.message.chat.id = 789

    data = _make_data()
    await middleware(failing_handler, update, data)

    args = data["bot"].send_message.call_args[0]
    assert args[0] == 789


@pytest.mark.asyncio
async def test_try_reply_non_update_event_does_nothing():
    """_try_reply silently returns if event is not an Update."""
    from aiogram.types import Message

    non_update = MagicMock(spec=Message)
    bot = AsyncMock()
    data = {"bot": bot}

    await _try_reply(non_update, data, "hello")
    bot.send_message.assert_not_called()
