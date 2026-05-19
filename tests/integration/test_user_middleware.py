"""
Integration tests for UserMiddleware and user get_or_create flow.
Tests use a real in-memory SQLite database.
"""

from typing import Any
from unittest.mock import MagicMock

from src.bot.middlewares.user import UserMiddleware
from src.db.models import User
from src.db.repositories.user_repo import UserRepository


async def test_first_message_creates_user(db_factory):
    async with db_factory() as session:
        repo = UserRepository(session)
        user, created = await repo.get_or_create(telegram_id=300001, username="han")
        await session.commit()

    assert created is True
    assert user.telegram_id == 300001
    assert user.username == "han"


async def test_second_message_returns_same_user(db_factory):
    async with db_factory() as session:
        repo = UserRepository(session)
        user1, created1 = await repo.get_or_create(telegram_id=300002, username="leia")
        await session.commit()

    async with db_factory() as session:
        repo = UserRepository(session)
        user2, created2 = await repo.get_or_create(telegram_id=300002, username="leia")
        await session.commit()

    assert created1 is True
    assert created2 is False
    assert user1.id == user2.id
    assert user1.telegram_id == user2.telegram_id


async def test_middleware_puts_user_in_data(db_factory):
    middleware = UserMiddleware(session_factory=db_factory)

    tg_user = MagicMock()
    tg_user.id = 400001
    tg_user.username = "luke"

    captured: dict[str, Any] = {}

    async def handler(event, data):
        captured.update(data)

    event = MagicMock()
    data: dict[str, Any] = {"event_from_user": tg_user}

    await middleware(handler, event, data)

    assert "user" in captured
    assert isinstance(captured["user"], User)
    assert captured["user"].telegram_id == 400001
    assert captured["user"].username == "luke"


async def test_middleware_same_user_on_repeated_calls(db_factory):
    middleware = UserMiddleware(session_factory=db_factory)

    tg_user = MagicMock()
    tg_user.id = 400002
    tg_user.username = "r2d2"

    users: list[User] = []

    async def handler(event, data):
        users.append(data["user"])

    for _ in range(2):
        event = MagicMock()
        data: dict[str, Any] = {"event_from_user": tg_user}
        await middleware(handler, event, data)

    assert len(users) == 2
    assert users[0].id == users[1].id


async def test_middleware_skips_when_no_telegram_user(db_factory):
    middleware = UserMiddleware(session_factory=db_factory)

    called = False

    async def handler(event, data):
        nonlocal called
        called = True
        assert "user" not in data

    event = MagicMock()
    data: dict[str, Any] = {}

    await middleware(handler, event, data)
    assert called
