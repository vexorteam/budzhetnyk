import json
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from src.bot.handlers.expense import handle_category_callback, handle_expense
from src.bot.keyboards.categories import CategoryCallback
from src.db.repositories.category_repo import CategoryRepository
from src.db.repositories.expense_repo import ExpenseRepository
from src.db.repositories.user_repo import UserRepository


async def _setup_db(db_factory):
    async with db_factory() as session:
        cat_repo = CategoryRepository(session)
        await cat_repo.seed_system_categories_if_empty()
        user_repo = UserRepository(session)
        user, _ = await user_repo.get_or_create(telegram_id=600001, username="tester")
        await session.commit()
        return user


def _make_fsm_context() -> FSMContext:
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=100, user_id=600001)
    return FSMContext(storage=storage, key=key)


async def test_expense_saved_with_auto_category(db_factory):
    user = await _setup_db(db_factory)
    state = _make_fsm_context()

    message = AsyncMock()
    message.text = "Кава 50"

    with patch("src.bot.handlers.expense.get_session_factory", return_value=db_factory):
        await handle_expense(message, user, state)

    async with db_factory() as session:
        repo = ExpenseRepository(session)
        expense = await repo.get_last_for_user(user.id)

    assert expense is not None
    assert expense.amount == Decimal("50")
    assert expense.description == "Кава"

    message.answer.assert_called_once()
    reply = message.answer.call_args[0][0]
    assert "50 грн" in reply
    assert "🍔" in reply
    assert "Їжа" in reply


async def test_parse_error_replies_with_hint(db_factory):
    user = await _setup_db(db_factory)
    state = _make_fsm_context()

    message = AsyncMock()
    message.text = "просто текст без числа"

    with patch("src.bot.handlers.expense.get_session_factory", return_value=db_factory):
        await handle_expense(message, user, state)

    async with db_factory() as session:
        repo = ExpenseRepository(session)
        expense = await repo.get_last_for_user(user.id)

    assert expense is None
    message.answer.assert_called_once()
    assert "Кава 50" in message.answer.call_args[0][0]


async def test_unknown_category_shows_keyboard(db_factory):
    user = await _setup_db(db_factory)
    state = _make_fsm_context()

    message = AsyncMock()
    message.text = "Абажур 300"

    with patch("src.bot.handlers.expense.get_session_factory", return_value=db_factory):
        await handle_expense(message, user, state)

    async with db_factory() as session:
        repo = ExpenseRepository(session)
        expense = await repo.get_last_for_user(user.id)

    assert expense is None
    message.answer.assert_called_once()
    call_kwargs = message.answer.call_args
    assert call_kwargs.kwargs.get("reply_markup") is not None


async def test_category_selection_and_learning(db_factory):
    """Абажур 800 → вибір Освіта → перевірка, що `абажур` в keywords персональної копії."""
    user = await _setup_db(db_factory)
    state = _make_fsm_context()

    message = AsyncMock()
    message.text = "Абажур 800"

    with patch("src.bot.handlers.expense.get_session_factory", return_value=db_factory):
        await handle_expense(message, user, state)

    # State should now hold pending data
    data = await state.get_data()
    assert data["pending_amount"] == "800"
    assert data["pending_description"] == "Абажур"

    # Find the education (Освіта) category id
    async with db_factory() as session:
        cat_repo = CategoryRepository(session)
        system_cats = await cat_repo.get_system_categories()
        education_cat = next(c for c in system_cats if c.system_code == "education")
        edu_id = education_cat.id

    # Simulate user selecting "Освіта"
    callback = AsyncMock()
    callback.message = AsyncMock()
    callback_data = CategoryCallback(category_id=edu_id)

    with patch("src.bot.handlers.expense.get_session_factory", return_value=db_factory):
        await handle_category_callback(callback, callback_data, state, user)

    # Expense should be saved
    async with db_factory() as session:
        repo = ExpenseRepository(session)
        expense = await repo.get_last_for_user(user.id)
        assert expense is not None
        assert expense.amount == Decimal("800")
        assert expense.description == "Абажур"

        # Personal copy of education should have "абажур" in keywords
        cat_repo = CategoryRepository(session)
        user_cats = await cat_repo.get_user_categories(user.id)
        edu_user_cat = next(
            (c for c in user_cats if c.system_code == "education"), None
        )
        assert edu_user_cat is not None
        keywords = json.loads(edu_user_cat.keywords)
        assert "абажур" in keywords

    # Confirm message was edited with learning note
    callback.message.edit_text.assert_called_once()
    reply = callback.message.edit_text.call_args[0][0]
    assert "800 грн" in reply
    assert "Освіта" in reply
    assert "🧠" in reply
    assert "Абажур" in reply

    # FSM state should be cleared
    current_state = await state.get_state()
    assert current_state is None


async def test_auto_categorization_after_learning(db_factory):
    """Повторне введення 'Абажур 900' після навчання → автокатегоризація без клавіатури."""
    user = await _setup_db(db_factory)

    # Pre-populate user's education category with "абажур"
    from src.services.categorizer import add_keyword_to_user_category

    async with db_factory() as session:
        await add_keyword_to_user_category(
            user_id=user.id,
            system_code="education",
            keyword="абажур",
            session=session,
        )
        await session.commit()

    state = _make_fsm_context()
    message = AsyncMock()
    message.text = "Абажур 900"

    with patch("src.bot.handlers.expense.get_session_factory", return_value=db_factory):
        await handle_expense(message, user, state)

    # Should auto-save without asking for category
    async with db_factory() as session:
        repo = ExpenseRepository(session)
        expense = await repo.get_last_for_user(user.id)

    assert expense is not None
    assert expense.amount == Decimal("900")

    message.answer.assert_called_once()
    reply = message.answer.call_args[0][0]
    assert "✅" in reply
    assert "900 грн" in reply
    # No keyboard shown
    call_kwargs = message.answer.call_args
    assert call_kwargs.kwargs.get("reply_markup") is None


async def test_number_only_shows_keyboard_no_keyword_added(db_factory):
    """Введення тільки числа `120` → клавіатура, але keyword не додається."""
    user = await _setup_db(db_factory)
    state = _make_fsm_context()

    message = AsyncMock()
    message.text = "120"

    with patch("src.bot.handlers.expense.get_session_factory", return_value=db_factory):
        await handle_expense(message, user, state)

    # Keyboard should be shown (description is None so category can't be guessed)
    message.answer.assert_called_once()
    call_kwargs = message.answer.call_args
    assert call_kwargs.kwargs.get("reply_markup") is not None

    data = await state.get_data()
    assert data["pending_amount"] == "120"
    assert data.get("pending_description") is None

    # Find any category to select
    async with db_factory() as session:
        cat_repo = CategoryRepository(session)
        system_cats = await cat_repo.get_system_categories()
        food_cat = next(c for c in system_cats if c.system_code == "food")
        food_id = food_cat.id

    callback = AsyncMock()
    callback.message = AsyncMock()
    callback_data = CategoryCallback(category_id=food_id)

    with patch("src.bot.handlers.expense.get_session_factory", return_value=db_factory):
        await handle_category_callback(callback, callback_data, state, user)

    async with db_factory() as session:
        repo = ExpenseRepository(session)
        expense = await repo.get_last_for_user(user.id)

        # No user personal copy should have been created (no keyword to learn)
        cat_repo = CategoryRepository(session)
        user_cats = await cat_repo.get_user_categories(user.id)
        food_user_cat = next((c for c in user_cats if c.system_code == "food"), None)

    assert expense is not None
    assert expense.amount == Decimal("120")
    assert expense.description is None
    assert food_user_cat is None  # no personal copy created

    # No 🧠 note in the reply
    reply = callback.message.edit_text.call_args[0][0]
    assert "🧠" not in reply


async def test_long_description_truncated_to_500(db_factory):
    """Description longer than 500 chars should be silently truncated."""
    user = await _setup_db(db_factory)
    state = _make_fsm_context()

    long_desc = "А" * 600
    message = AsyncMock()
    message.text = f"{long_desc} 99"

    with patch("src.bot.handlers.expense.get_session_factory", return_value=db_factory):
        await handle_expense(message, user, state)

    async with db_factory() as session:
        repo = ExpenseRepository(session)
        expense = await repo.get_last_for_user(user.id)

    # Should still show keyboard (long nonsense not in keywords), but description is saved
    # Either auto-saved or pending — check that FSM data description is ≤ 500
    fsm_data = await state.get_data()
    pending_desc = fsm_data.get("pending_description")
    if pending_desc is not None:
        assert len(pending_desc) <= 500
    elif expense is not None:
        assert expense.description is None or len(expense.description) <= 500
