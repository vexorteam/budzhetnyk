from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.db.models import Category, Expense
from src.db.repositories.category_repo import CategoryRepository
from src.db.repositories.user_repo import UserRepository
from src.exceptions import InvalidPeriodError
from src.services.statistics import CategoryStat, PeriodStats, get_period_stats


async def _setup(db_session):
    user_repo = UserRepository(db_session)
    cat_repo = CategoryRepository(db_session)
    user, _ = await user_repo.get_or_create(telegram_id=700001, username="statuser")
    await cat_repo.seed_system_categories_if_empty()
    await db_session.commit()
    return user


async def _get_cat(db_session, system_code: str) -> Category:
    from sqlalchemy import select

    result = await db_session.execute(
        select(Category).where(
            Category.system_code == system_code, Category.user_id.is_(None)
        )
    )
    return result.scalars().first()


async def _add_expense(
    db_session,
    user_id: int,
    system_code: str,
    amount: Decimal,
    created_at: datetime,
    description: str | None = None,
) -> Expense:
    cat = await _get_cat(db_session, system_code)
    expense = Expense(
        user_id=user_id,
        category_id=cat.id,
        amount=amount,
        description=description,
        created_at=created_at,
    )
    db_session.add(expense)
    await db_session.flush()
    return expense


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def test_empty_period_returns_zero_stats(db_session):
    user = await _setup(db_session)
    stats = await get_period_stats(user.id, "month", db_session)

    assert stats.total == Decimal("0")
    assert stats.by_category == []
    assert stats.top_expenses == []
    assert "Статистика" not in stats.period_label  # just a label string


async def test_period_label_month(db_session):
    user = await _setup(db_session)
    stats = await get_period_stats(user.id, "month", db_session)
    now = _now()
    assert str(now.year) in stats.period_label


async def test_period_label_day(db_session):
    user = await _setup(db_session)
    stats = await get_period_stats(user.id, "day", db_session)
    assert str(_now().year) in stats.period_label


async def test_period_label_week(db_session):
    user = await _setup(db_session)
    stats = await get_period_stats(user.id, "week", db_session)
    assert stats.period_label == "останні 7 днів"


async def test_period_label_year(db_session):
    user = await _setup(db_session)
    stats = await get_period_stats(user.id, "year", db_session)
    assert stats.period_label == str(_now().year)


async def test_invalid_period_raises(db_session):
    user = await _setup(db_session)
    with pytest.raises(InvalidPeriodError) as exc_info:
        await get_period_stats(user.id, "foo", db_session)
    assert exc_info.value.period == "foo"


async def test_single_category_total(db_session):
    user = await _setup(db_session)
    now = _now()
    month_start = now.replace(day=1, hour=12, minute=0, second=0, microsecond=0)

    await _add_expense(db_session, user.id, "food", Decimal("100"), month_start)
    await _add_expense(db_session, user.id, "food", Decimal("250"), month_start)
    await db_session.commit()

    stats = await get_period_stats(user.id, "month", db_session)

    assert stats.total == Decimal("350")
    assert len(stats.by_category) == 1
    assert stats.by_category[0].total == Decimal("350")
    assert stats.by_category[0].percent == Decimal("100")
    assert stats.by_category[0].emoji == "🍔"
    assert stats.by_category[0].name == "Їжа"


async def test_multiple_categories_sorted_by_total(db_session):
    user = await _setup(db_session)
    now = _now()
    d = now.replace(day=1, hour=12, minute=0, second=0, microsecond=0)

    await _add_expense(db_session, user.id, "food", Decimal("300"), d)
    await _add_expense(db_session, user.id, "transport", Decimal("200"), d)
    await _add_expense(db_session, user.id, "utilities", Decimal("500"), d)
    await db_session.commit()

    stats = await get_period_stats(user.id, "month", db_session)

    assert stats.total == Decimal("1000")
    assert len(stats.by_category) == 3
    # sorted descending by total
    assert stats.by_category[0].total == Decimal("500")
    assert stats.by_category[1].total == Decimal("300")
    assert stats.by_category[2].total == Decimal("200")


async def test_percents_sum_to_100(db_session):
    user = await _setup(db_session)
    now = _now()
    d = now.replace(day=1, hour=12, minute=0, second=0, microsecond=0)

    await _add_expense(db_session, user.id, "food", Decimal("300"), d)
    await _add_expense(db_session, user.id, "transport", Decimal("200"), d)
    await _add_expense(db_session, user.id, "utilities", Decimal("500"), d)
    await db_session.commit()

    stats = await get_period_stats(user.id, "month", db_session)

    total_pct = sum(cs.percent for cs in stats.by_category)
    # Rounding to nearest int per category, so allow ±2 due to rounding
    assert abs(total_pct - 100) <= 2


async def test_top_3_expenses_by_amount(db_session):
    user = await _setup(db_session)
    now = _now()
    d = now.replace(day=1, hour=12, minute=0, second=0, microsecond=0)

    await _add_expense(db_session, user.id, "food", Decimal("50"), d)
    await _add_expense(db_session, user.id, "food", Decimal("500"), d)
    await _add_expense(db_session, user.id, "food", Decimal("100"), d)
    await _add_expense(db_session, user.id, "food", Decimal("300"), d)
    await db_session.commit()

    stats = await get_period_stats(user.id, "month", db_session)

    assert len(stats.top_expenses) == 3
    assert stats.top_expenses[0].amount == Decimal("500")
    assert stats.top_expenses[1].amount == Decimal("300")
    assert stats.top_expenses[2].amount == Decimal("100")


async def test_top_expenses_fewer_than_3(db_session):
    user = await _setup(db_session)
    now = _now()
    d = now.replace(day=1, hour=12, minute=0, second=0, microsecond=0)

    await _add_expense(db_session, user.id, "food", Decimal("100"), d)
    await _add_expense(db_session, user.id, "food", Decimal("200"), d)
    await db_session.commit()

    stats = await get_period_stats(user.id, "month", db_session)

    assert len(stats.top_expenses) == 2


async def test_previous_month_excluded(db_session):
    user = await _setup(db_session)
    now = _now()
    current_month = now.replace(day=1, hour=12, minute=0, second=0, microsecond=0)
    last_month = (now.replace(day=1) - timedelta(days=1)).replace(
        hour=12, minute=0, second=0, microsecond=0
    )

    await _add_expense(db_session, user.id, "food", Decimal("100"), current_month)
    await _add_expense(db_session, user.id, "food", Decimal("200"), last_month)
    await db_session.commit()

    stats = await get_period_stats(user.id, "month", db_session)

    assert stats.total == Decimal("100")


async def test_day_period_excludes_yesterday(db_session):
    user = await _setup(db_session)
    now = _now()
    today = now.replace(hour=12, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)

    await _add_expense(db_session, user.id, "food", Decimal("100"), today)
    await _add_expense(db_session, user.id, "food", Decimal("200"), yesterday)
    await db_session.commit()

    stats = await get_period_stats(user.id, "day", db_session)

    assert stats.total == Decimal("100")


async def test_week_period_excludes_8_days_ago(db_session):
    user = await _setup(db_session)
    now = _now()
    today = now.replace(hour=12, minute=0, second=0, microsecond=0)
    three_days_ago = today - timedelta(days=3)
    eight_days_ago = today - timedelta(days=8)

    await _add_expense(db_session, user.id, "food", Decimal("100"), today)
    await _add_expense(db_session, user.id, "food", Decimal("200"), three_days_ago)
    await _add_expense(db_session, user.id, "food", Decimal("300"), eight_days_ago)
    await db_session.commit()

    stats = await get_period_stats(user.id, "week", db_session)

    assert stats.total == Decimal("300")  # today + three_days_ago


async def test_year_period_excludes_last_year(db_session):
    user = await _setup(db_session)
    now = _now()
    this_year = now.replace(month=1, day=2, hour=12, minute=0, second=0, microsecond=0)
    last_year = this_year.replace(year=now.year - 1)

    await _add_expense(db_session, user.id, "food", Decimal("100"), this_year)
    await _add_expense(db_session, user.id, "food", Decimal("200"), last_year)
    await db_session.commit()

    stats = await get_period_stats(user.id, "year", db_session)

    assert stats.total == Decimal("100")


async def test_category_stat_fields(db_session):
    user = await _setup(db_session)
    now = _now()
    d = now.replace(day=1, hour=12, minute=0, second=0, microsecond=0)

    cat = await _get_cat(db_session, "transport")
    await _add_expense(db_session, user.id, "transport", Decimal("400"), d)
    await db_session.commit()

    stats = await get_period_stats(user.id, "month", db_session)

    cs = stats.by_category[0]
    assert cs.category_id == cat.id
    assert cs.name == "Транспорт"
    assert cs.emoji == "🚇"
    assert cs.total == Decimal("400")


async def test_personal_and_system_copy_merged_into_one_category(db_session):
    """Expenses under system category and its personal copy must appear as one row."""
    user = await _setup(db_session)
    now = _now()
    d = now.replace(day=1, hour=12, minute=0, second=0, microsecond=0)

    # Expense under system shopping category
    await _add_expense(db_session, user.id, "shopping", Decimal("150"), d)

    # Create personal copy of shopping and add an expense to it
    from src.services.categorizer import add_keyword_to_user_category

    await add_keyword_to_user_category(
        user_id=user.id, system_code="shopping", keyword="магазин", session=db_session
    )
    await db_session.flush()

    # Find the personal copy
    from sqlalchemy import select

    result = await db_session.execute(
        select(Category).where(
            Category.system_code == "shopping", Category.user_id == user.id
        )
    )
    personal_cat = result.scalars().first()
    assert personal_cat is not None

    expense2 = Expense(
        user_id=user.id,
        category_id=personal_cat.id,
        amount=Decimal("170"),
        description="щось",
        created_at=d,
    )
    db_session.add(expense2)
    await db_session.commit()

    stats = await get_period_stats(user.id, "month", db_session)

    shopping_stats = [cs for cs in stats.by_category if cs.emoji == "🛒"]
    assert len(shopping_stats) == 1, "shopping must appear exactly once"
    assert shopping_stats[0].total == Decimal("320")


async def test_top_expenses_have_category_loaded(db_session):
    user = await _setup(db_session)
    now = _now()
    d = now.replace(day=1, hour=12, minute=0, second=0, microsecond=0)

    await _add_expense(
        db_session, user.id, "health", Decimal("800"), d, description="Аптека"
    )
    await db_session.commit()

    stats = await get_period_stats(user.id, "month", db_session)

    assert len(stats.top_expenses) == 1
    assert stats.top_expenses[0].category.emoji == "💊"
    assert stats.top_expenses[0].description == "Аптека"
