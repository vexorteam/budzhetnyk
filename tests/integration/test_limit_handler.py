from decimal import Decimal
from unittest.mock import AsyncMock, patch

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from src.bot.handlers.expense import handle_expense
from src.bot.handlers.limit import handle_limit
from src.db.repositories.category_repo import CategoryRepository
from src.db.repositories.user_repo import UserRepository


async def _setup_db(db_factory, telegram_id: int = 800001):
    async with db_factory() as session:
        cat_repo = CategoryRepository(session)
        await cat_repo.seed_system_categories_if_empty()
        user_repo = UserRepository(session)
        user, _ = await user_repo.get_or_create(telegram_id=telegram_id, username="limituser")
        await session.commit()
        return user


def _make_fsm(user_id: int = 800001) -> FSMContext:
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=100, user_id=user_id)
    return FSMContext(storage=storage, key=key)


async def test_limit_show_when_not_set(db_factory):
    user = await _setup_db(db_factory)

    message = AsyncMock()
    message.text = "/limit"

    with patch("src.bot.handlers.limit.get_session_factory", return_value=db_factory):
        await handle_limit(message, user)

    message.answer.assert_called_once()
    reply = message.answer.call_args[0][0]
    assert "не встановлено" in reply.lower()


async def test_limit_set(db_factory):
    user = await _setup_db(db_factory)

    message = AsyncMock()
    message.text = "/limit 10000"

    with patch("src.bot.handlers.limit.get_session_factory", return_value=db_factory):
        await handle_limit(message, user)

    message.answer.assert_called_once()
    reply = message.answer.call_args[0][0]
    assert "10 000 грн" in reply

    async with db_factory() as session:
        repo = UserRepository(session)
        found = await repo.get_by_telegram_id(800001)
    assert found.monthly_limit == Decimal("10000")


async def test_limit_off(db_factory):
    user = await _setup_db(db_factory)

    async with db_factory() as session:
        repo = UserRepository(session)
        await repo.set_monthly_limit(user.id, Decimal("5000"))
        await session.commit()
    user.monthly_limit = Decimal("5000")

    message = AsyncMock()
    message.text = "/limit off"

    with patch("src.bot.handlers.limit.get_session_factory", return_value=db_factory):
        await handle_limit(message, user)

    message.answer.assert_called_once()
    assert "вимкнено" in message.answer.call_args[0][0].lower()

    async with db_factory() as session:
        repo = UserRepository(session)
        found = await repo.get_by_telegram_id(800001)
    assert found.monthly_limit is None


async def test_limit_show_when_set(db_factory):
    user = await _setup_db(db_factory)
    user.monthly_limit = Decimal("3000")

    message = AsyncMock()
    message.text = "/limit"

    with patch("src.bot.handlers.limit.get_session_factory", return_value=db_factory):
        await handle_limit(message, user)

    reply = message.answer.call_args[0][0]
    assert "3 000 грн" in reply


async def test_limit_invalid_negative(db_factory):
    user = await _setup_db(db_factory)

    message = AsyncMock()
    message.text = "/limit -100"

    with patch("src.bot.handlers.limit.get_session_factory", return_value=db_factory):
        await handle_limit(message, user)

    message.answer.assert_called_once()
    reply = message.answer.call_args[0][0]
    assert "більше 0" in reply.lower() or "невірн" in reply.lower()


async def test_limit_invalid_text(db_factory):
    user = await _setup_db(db_factory)

    message = AsyncMock()
    message.text = "/limit abc"

    with patch("src.bot.handlers.limit.get_session_factory", return_value=db_factory):
        await handle_limit(message, user)

    message.answer.assert_called_once()
    reply = message.answer.call_args[0][0]
    assert "невірне" in reply.lower() or "числ" in reply.lower()


async def test_expense_warns_at_80_percent(db_factory):
    """Expense that brings total to ≥80% triggers a warning."""
    user = await _setup_db(db_factory, telegram_id=800002)

    async with db_factory() as session:
        repo = UserRepository(session)
        await repo.set_monthly_limit(user.id, Decimal("1000"))
        await session.commit()
    user.monthly_limit = Decimal("1000")

    # Add expense of 799 grn — 79.9%, no warning
    state = _make_fsm(user_id=800002)
    msg1 = AsyncMock()
    msg1.text = "Кава 799"

    with patch("src.bot.handlers.expense.get_session_factory", return_value=db_factory):
        await handle_expense(msg1, user, state)

    reply1 = msg1.answer.call_args[0][0]
    assert "⚠️" not in reply1
    assert "🚨" not in reply1

    # Add expense of 2 grn — total = 801 grn (80.1%) → warning
    state2 = _make_fsm(user_id=800002)
    msg2 = AsyncMock()
    msg2.text = "Кава 2"

    with patch("src.bot.handlers.expense.get_session_factory", return_value=db_factory):
        await handle_expense(msg2, user, state2)

    reply2 = msg2.answer.call_args[0][0]
    assert "⚠️" in reply2
    assert "1 000 грн" in reply2


async def test_expense_warns_repeatedly_above_80(db_factory):
    """Every subsequent expense while total ≥80% (but <100%) shows a warning."""
    user = await _setup_db(db_factory, telegram_id=800006)

    async with db_factory() as session:
        repo = UserRepository(session)
        await repo.set_monthly_limit(user.id, Decimal("1000"))
        await session.commit()
    user.monthly_limit = Decimal("1000")

    for i, amount in enumerate(["810", "50", "30"], start=1):
        state = _make_fsm(user_id=800006)
        msg = AsyncMock()
        msg.text = f"Кава {amount}"
        with patch("src.bot.handlers.expense.get_session_factory", return_value=db_factory):
            await handle_expense(msg, user, state)
        reply = msg.answer.call_args[0][0]
        assert "⚠️" in reply or "🚨" in reply, f"Expected warning on expense #{i}"


async def test_expense_warns_at_100_percent(db_factory):
    """Expense that brings total to ≥100% triggers a critical warning."""
    user = await _setup_db(db_factory, telegram_id=800003)

    async with db_factory() as session:
        repo = UserRepository(session)
        await repo.set_monthly_limit(user.id, Decimal("500"))
        await session.commit()
    user.monthly_limit = Decimal("500")

    # Add expense of 490 — 98% → ⚠️ (≥80% warning)
    state = _make_fsm(user_id=800003)
    msg1 = AsyncMock()
    msg1.text = "Оренда 490"

    with patch("src.bot.handlers.expense.get_session_factory", return_value=db_factory):
        await handle_expense(msg1, user, state)

    reply1 = msg1.answer.call_args[0][0]
    assert "⚠️" in reply1
    assert "🚨" not in reply1

    # Add expense of 11 — total = 501 (100.2%) → 🚨
    state2 = _make_fsm(user_id=800003)
    msg2 = AsyncMock()
    msg2.text = "Кава 11"

    with patch("src.bot.handlers.expense.get_session_factory", return_value=db_factory):
        await handle_expense(msg2, user, state2)

    reply2 = msg2.answer.call_args[0][0]
    assert "🚨" in reply2
    assert "500 грн" in reply2


async def test_expense_no_warning_without_limit(db_factory):
    """No limit set — no warning messages."""
    user = await _setup_db(db_factory, telegram_id=800004)

    state = _make_fsm(user_id=800004)
    msg = AsyncMock()
    msg.text = "Кава 9999"

    with patch("src.bot.handlers.expense.get_session_factory", return_value=db_factory):
        await handle_expense(msg, user, state)

    reply = msg.answer.call_args[0][0]
    assert "⚠️" not in reply
    assert "🚨" not in reply


async def test_expense_shows_current_percent_in_warning(db_factory):
    """Warning message contains the actual current percentage, not a fixed '80%'."""
    user = await _setup_db(db_factory, telegram_id=800005)

    async with db_factory() as session:
        repo = UserRepository(session)
        await repo.set_monthly_limit(user.id, Decimal("1000"))
        await session.commit()
    user.monthly_limit = Decimal("1000")

    state = _make_fsm(user_id=800005)
    msg = AsyncMock()
    msg.text = "Кава 900"  # 90% of limit

    with patch("src.bot.handlers.expense.get_session_factory", return_value=db_factory):
        await handle_expense(msg, user, state)

    reply = msg.answer.call_args[0][0]
    assert "⚠️" in reply
    assert "90%" in reply
