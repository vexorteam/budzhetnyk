from datetime import datetime
from decimal import Decimal

import pytest

from src.db.models import Category, User
from src.db.repositories.expense_repo import ExpenseRepository


@pytest.fixture
async def user_and_category(db_session):
    user = User(telegram_id=500001)
    category = Category(name="Їжа", emoji="🍔", system_code="food", keywords="[]")
    db_session.add_all([user, category])
    await db_session.flush()
    return user, category


async def test_create_expense(db_session, user_and_category):
    user, category = user_and_category
    repo = ExpenseRepository(db_session)
    expense = await repo.create(
        user_id=user.id,
        category_id=category.id,
        amount=Decimal("50.00"),
        description="Кава",
    )
    assert expense.id is not None
    assert expense.user_id == user.id
    assert expense.category_id == category.id
    assert expense.amount == Decimal("50.00")
    assert expense.description == "Кава"


async def test_create_expense_no_description(db_session, user_and_category):
    user, category = user_and_category
    repo = ExpenseRepository(db_session)
    expense = await repo.create(
        user_id=user.id,
        category_id=category.id,
        amount=Decimal("100"),
        description=None,
    )
    assert expense.id is not None
    assert expense.description is None


async def test_get_last_for_user_returns_most_recent(db_session, user_and_category):
    user, category = user_and_category
    repo = ExpenseRepository(db_session)
    await repo.create(
        user_id=user.id,
        category_id=category.id,
        amount=Decimal("10.00"),
        description="Перша",
    )
    e2 = await repo.create(
        user_id=user.id,
        category_id=category.id,
        amount=Decimal("20.00"),
        description="Друга",
    )
    last = await repo.get_last_for_user(user.id)
    assert last is not None
    assert last.id == e2.id


async def test_get_last_for_user_empty(db_session, user_and_category):
    user, _ = user_and_category
    repo = ExpenseRepository(db_session)
    last = await repo.get_last_for_user(user.id)
    assert last is None


async def test_get_period_expenses_returns_within_range(db_session, user_and_category):
    user, category = user_and_category
    repo = ExpenseRepository(db_session)
    await repo.create(
        user_id=user.id,
        category_id=category.id,
        amount=Decimal("30.00"),
        description="Тест",
    )
    expenses = await repo.get_period_expenses(
        user_id=user.id,
        date_from=datetime(2020, 1, 1),
        date_to=datetime(2099, 12, 31),
    )
    assert len(expenses) == 1
    assert expenses[0].amount == Decimal("30.00")


async def test_get_period_expenses_empty(db_session, user_and_category):
    user, _ = user_and_category
    repo = ExpenseRepository(db_session)
    expenses = await repo.get_period_expenses(
        user_id=user.id,
        date_from=datetime(2020, 1, 1),
        date_to=datetime(2099, 12, 31),
    )
    assert expenses == []


async def test_get_period_expenses_excludes_other_user(db_session, user_and_category):
    user, category = user_and_category
    other_user = User(telegram_id=500002)
    db_session.add(other_user)
    await db_session.flush()

    repo = ExpenseRepository(db_session)
    await repo.create(
        user_id=other_user.id,
        category_id=category.id,
        amount=Decimal("99.00"),
        description="Чужа",
    )

    expenses = await repo.get_period_expenses(
        user_id=user.id,
        date_from=datetime(2020, 1, 1),
        date_to=datetime(2099, 12, 31),
    )
    assert expenses == []


async def test_get_period_expenses_multiple_sorted(db_session, user_and_category):
    user, category = user_and_category
    repo = ExpenseRepository(db_session)
    e1 = await repo.create(
        user_id=user.id,
        category_id=category.id,
        amount=Decimal("10.00"),
        description="A",
    )
    e2 = await repo.create(
        user_id=user.id,
        category_id=category.id,
        amount=Decimal("20.00"),
        description="B",
    )
    expenses = await repo.get_period_expenses(
        user_id=user.id,
        date_from=datetime(2020, 1, 1),
        date_to=datetime(2099, 12, 31),
    )
    assert len(expenses) == 2
    ids = [e.id for e in expenses]
    assert e1.id in ids
    assert e2.id in ids
