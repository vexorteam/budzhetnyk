import json
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.db.models import Base, Category, Expense, User


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as s:
        yield s
    await engine.dispose()


async def test_create_user(session: AsyncSession):
    user = User(telegram_id=123456789, username="testuser")
    session.add(user)
    await session.commit()
    await session.refresh(user)

    assert user.id is not None
    assert user.telegram_id == 123456789
    assert user.username == "testuser"
    assert user.monthly_limit is None
    assert user.created_at is not None


async def test_create_system_category(session: AsyncSession):
    category = Category(
        user_id=None,
        name="Їжа",
        emoji="🍔",
        keywords=json.dumps(["кава", "обід"]),
        system_code="food",
    )
    session.add(category)
    await session.commit()
    await session.refresh(category)

    assert category.id is not None
    assert category.user_id is None
    assert category.system_code == "food"
    assert json.loads(category.keywords) == ["кава", "обід"]


async def test_create_user_category(session: AsyncSession):
    user = User(telegram_id=111, username="u1")
    session.add(user)
    await session.commit()

    category = Category(
        user_id=user.id,
        name="Освіта",
        emoji="📚",
        keywords=json.dumps(["курс"]),
        system_code="education",
    )
    session.add(category)
    await session.commit()
    await session.refresh(category)

    assert category.user_id == user.id


async def test_create_expense_with_relations(session: AsyncSession):
    user = User(telegram_id=222, username="u2")
    session.add(user)
    await session.commit()

    category = Category(
        user_id=None,
        name="Їжа",
        emoji="🍔",
        keywords=json.dumps(["кава"]),
        system_code="food",
    )
    session.add(category)
    await session.commit()

    expense = Expense(
        user_id=user.id,
        category_id=category.id,
        amount=Decimal("50.00"),
        description="Кава",
    )
    session.add(expense)
    await session.commit()
    await session.refresh(expense)

    assert expense.id is not None
    assert expense.amount == Decimal("50.00")
    assert expense.description == "Кава"
    assert expense.created_at is not None


async def test_user_expenses_relationship(session: AsyncSession):
    user = User(telegram_id=333, username="u3")
    session.add(user)
    await session.commit()

    category = Category(
        user_id=None,
        name="Транспорт",
        emoji="🚇",
        keywords=json.dumps(["метро"]),
        system_code="transport",
    )
    session.add(category)
    await session.commit()

    for i in range(3):
        expense = Expense(
            user_id=user.id,
            category_id=category.id,
            amount=Decimal(f"{(i + 1) * 10}.00"),
            description=f"витрата {i}",
        )
        session.add(expense)
    await session.commit()

    await session.refresh(user)
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    stmt = select(User).where(User.id == user.id).options(selectinload(User.expenses))
    result = await session.execute(stmt)
    loaded_user = result.scalar_one()

    assert len(loaded_user.expenses) == 3


async def test_category_expenses_relationship(session: AsyncSession):
    user = User(telegram_id=444, username="u4")
    session.add(user)
    await session.commit()

    category = Category(
        user_id=None,
        name="Розваги",
        emoji="🎮",
        keywords=json.dumps(["кіно"]),
        system_code="entertainment",
    )
    session.add(category)
    await session.commit()

    expense = Expense(
        user_id=user.id,
        category_id=category.id,
        amount=Decimal("200.00"),
        description="Кіно",
    )
    session.add(expense)
    await session.commit()

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    stmt = (
        select(Category)
        .where(Category.id == category.id)
        .options(selectinload(Category.expenses))
    )
    result = await session.execute(stmt)
    loaded_cat = result.scalar_one()

    assert len(loaded_cat.expenses) == 1
    assert loaded_cat.expenses[0].description == "Кіно"


async def test_expense_user_and_category_relationship(session: AsyncSession):
    user = User(telegram_id=555, username="u5")
    session.add(user)
    await session.commit()

    category = Category(
        user_id=None,
        name="Покупки",
        emoji="🛒",
        keywords=json.dumps(["одяг"]),
        system_code="shopping",
    )
    session.add(category)
    await session.commit()

    expense = Expense(
        user_id=user.id,
        category_id=category.id,
        amount=Decimal("999.99"),
        description="Кросівки",
    )
    session.add(expense)
    await session.commit()

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    stmt = (
        select(Expense)
        .where(Expense.id == expense.id)
        .options(selectinload(Expense.user), selectinload(Expense.category))
    )
    result = await session.execute(stmt)
    loaded_exp = result.scalar_one()

    assert loaded_exp.user.telegram_id == 555
    assert loaded_exp.category.name == "Покупки"


async def test_user_unique_telegram_id(session: AsyncSession):
    user1 = User(telegram_id=999, username="u_a")
    session.add(user1)
    await session.commit()

    user2 = User(telegram_id=999, username="u_b")
    session.add(user2)
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_monthly_limit_stored_as_decimal(session: AsyncSession):
    user = User(telegram_id=777, username="u7", monthly_limit=Decimal("10000.00"))
    session.add(user)
    await session.commit()
    await session.refresh(user)

    assert user.monthly_limit == Decimal("10000.00")
