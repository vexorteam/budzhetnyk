from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.user_repo import UserRepository
from src.exceptions import UserNotFoundError


async def test_create_user(db_session: AsyncSession):
    repo = UserRepository(db_session)
    user = await repo.create(telegram_id=100001, username="alice")
    await db_session.commit()

    assert user.id is not None
    assert user.telegram_id == 100001
    assert user.username == "alice"


async def test_create_user_without_username(db_session: AsyncSession):
    repo = UserRepository(db_session)
    user = await repo.create(telegram_id=100002)
    await db_session.commit()

    assert user.username is None


async def test_get_by_telegram_id_found(db_session: AsyncSession):
    repo = UserRepository(db_session)
    await repo.create(telegram_id=100003, username="bob")
    await db_session.commit()

    found = await repo.get_by_telegram_id(100003)
    assert found.username == "bob"


async def test_get_by_telegram_id_not_found(db_session: AsyncSession):
    repo = UserRepository(db_session)
    with pytest.raises(UserNotFoundError) as exc_info:
        await repo.get_by_telegram_id(999999)
    assert exc_info.value.telegram_id == 999999


async def test_get_or_create_creates_new_user(db_session: AsyncSession):
    repo = UserRepository(db_session)
    user, created = await repo.get_or_create(telegram_id=200001, username="carol")
    await db_session.commit()

    assert created is True
    assert user.telegram_id == 200001


async def test_get_or_create_returns_existing_user(db_session: AsyncSession):
    repo = UserRepository(db_session)
    user1, created1 = await repo.get_or_create(telegram_id=200002, username="dave")
    await db_session.commit()

    user2, created2 = await repo.get_or_create(telegram_id=200002, username="dave")
    await db_session.commit()

    assert created1 is True
    assert created2 is False
    assert user1.id == user2.id


async def test_get_or_create_idempotent_on_same_session(db_session: AsyncSession):
    repo = UserRepository(db_session)
    user_a, _ = await repo.get_or_create(telegram_id=200003)
    user_b, created = await repo.get_or_create(telegram_id=200003)

    assert created is False
    assert user_a.telegram_id == user_b.telegram_id


async def test_set_monthly_limit(db_session: AsyncSession):
    repo = UserRepository(db_session)
    user = await repo.create(telegram_id=300001, username="limittest")
    await db_session.commit()

    await repo.set_monthly_limit(user.id, Decimal("10000"))
    await db_session.commit()

    found = await repo.get_by_telegram_id(300001)
    assert found.monthly_limit == Decimal("10000")


async def test_set_monthly_limit_to_none(db_session: AsyncSession):
    repo = UserRepository(db_session)
    user = await repo.create(telegram_id=300002, username="limitoff")
    await db_session.commit()

    await repo.set_monthly_limit(user.id, Decimal("5000"))
    await db_session.commit()

    await repo.set_monthly_limit(user.id, None)
    await db_session.commit()

    found = await repo.get_by_telegram_id(300002)
    assert found.monthly_limit is None
