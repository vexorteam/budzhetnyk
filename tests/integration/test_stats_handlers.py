from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from src.bot.handlers.stats import handle_stats
from src.db.models import Category, Expense
from src.db.repositories.category_repo import CategoryRepository
from src.db.repositories.user_repo import UserRepository


async def _setup_db(db_factory):
    async with db_factory() as session:
        cat_repo = CategoryRepository(session)
        await cat_repo.seed_system_categories_if_empty()
        user_repo = UserRepository(session)
        user, _ = await user_repo.get_or_create(
            telegram_id=800001, username="statshandler"
        )
        await session.commit()
        return user


async def _create_expense(
    db_factory, user_id: int, amount: float, system_code: str = "food"
):
    from sqlalchemy import select

    async with db_factory() as session:
        result = await session.execute(
            select(Category).where(
                Category.system_code == system_code, Category.user_id.is_(None)
            )
        )
        cat = result.scalars().first()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        expense = Expense(
            user_id=user_id,
            category_id=cat.id,
            amount=Decimal(str(amount)),
            description="тест",
            created_at=now,
        )
        session.add(expense)
        await session.commit()


def _make_command(args: str | None) -> MagicMock:
    cmd = MagicMock()
    cmd.args = args
    return cmd


async def test_stats_no_expenses_returns_empty_message(db_factory):
    user = await _setup_db(db_factory)
    message = AsyncMock()

    with patch("src.bot.handlers.stats.get_session_factory", return_value=db_factory):
        await handle_stats(message, user, _make_command(None))

    message.answer.assert_called_once()
    reply = message.answer.call_args[0][0]
    assert "Статистика" in reply
    assert "Витрат ще немає" in reply


async def test_stats_default_period_is_month(db_factory):
    user = await _setup_db(db_factory)
    await _create_expense(db_factory, user.id, 500)

    message = AsyncMock()

    with patch("src.bot.handlers.stats.get_session_factory", return_value=db_factory):
        await handle_stats(message, user, _make_command(None))

    message.answer.assert_called_once()
    reply = message.answer.call_args[0][0]
    assert "500" in reply
    assert "🍔" in reply
    assert "Їжа" in reply


async def test_stats_shows_total(db_factory):
    user = await _setup_db(db_factory)
    await _create_expense(db_factory, user.id, 200, "food")
    await _create_expense(db_factory, user.id, 300, "transport")

    message = AsyncMock()

    with patch("src.bot.handlers.stats.get_session_factory", return_value=db_factory):
        await handle_stats(message, user, _make_command(None))

    reply = message.answer.call_args[0][0]
    assert "500" in reply


async def test_stats_week_period(db_factory):
    user = await _setup_db(db_factory)
    await _create_expense(db_factory, user.id, 150, "transport")

    message = AsyncMock()

    with patch("src.bot.handlers.stats.get_session_factory", return_value=db_factory):
        await handle_stats(message, user, _make_command("week"))

    message.answer.assert_called_once()
    reply = message.answer.call_args[0][0]
    assert "останні 7 днів" in reply
    assert "150" in reply


async def test_stats_day_period(db_factory):
    user = await _setup_db(db_factory)
    await _create_expense(db_factory, user.id, 75, "food")

    message = AsyncMock()

    with patch("src.bot.handlers.stats.get_session_factory", return_value=db_factory):
        await handle_stats(message, user, _make_command("day"))

    message.answer.assert_called_once()
    reply = message.answer.call_args[0][0]
    assert "75" in reply


async def test_stats_year_period(db_factory):
    user = await _setup_db(db_factory)
    await _create_expense(db_factory, user.id, 999, "shopping")

    message = AsyncMock()

    with patch("src.bot.handlers.stats.get_session_factory", return_value=db_factory):
        await handle_stats(message, user, _make_command("year"))

    message.answer.assert_called_once()
    reply = message.answer.call_args[0][0]
    assert "999" in reply


async def test_stats_invalid_period_friendly_response(db_factory):
    user = await _setup_db(db_factory)
    message = AsyncMock()

    with patch("src.bot.handlers.stats.get_session_factory", return_value=db_factory):
        await handle_stats(message, user, _make_command("foo"))

    message.answer.assert_called_once()
    reply = message.answer.call_args[0][0]
    assert "Невідомий" in reply
    assert "day" in reply


async def test_stats_with_limit_shows_limit(db_factory):
    user = await _setup_db(db_factory)
    user.monthly_limit = Decimal("10000")
    await _create_expense(db_factory, user.id, 2500, "food")

    message = AsyncMock()

    with patch("src.bot.handlers.stats.get_session_factory", return_value=db_factory):
        await handle_stats(message, user, _make_command(None))

    reply = message.answer.call_args[0][0]
    assert "2 500" in reply
    assert "10 000" in reply
    assert "ліміту" in reply


async def test_stats_limit_not_shown_for_week(db_factory):
    user = await _setup_db(db_factory)
    user.monthly_limit = Decimal("10000")
    await _create_expense(db_factory, user.id, 100, "food")

    message = AsyncMock()

    with patch("src.bot.handlers.stats.get_session_factory", return_value=db_factory):
        await handle_stats(message, user, _make_command("week"))

    reply = message.answer.call_args[0][0]
    assert "ліміту" not in reply
