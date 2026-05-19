import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Category, User
from src.db.repositories.category_repo import CategoryRepository
from src.exceptions import InvalidKeywordError
from src.services.categorizer import add_keyword_to_user_category, guess_category


async def _seed(session: AsyncSession) -> None:
    repo = CategoryRepository(session)
    await repo.seed_system_categories_if_empty()
    await session.commit()


async def _make_user(session: AsyncSession, telegram_id: int = 100001) -> User:
    user = User(telegram_id=telegram_id, username="testuser")
    session.add(user)
    await session.flush()
    return user


# ---------------------------------------------------------------------------
# guess_category — system categories
# ---------------------------------------------------------------------------


async def test_guess_category_food_keyword(db_session: AsyncSession):
    await _seed(db_session)
    user = await _make_user(db_session)

    result = await guess_category("кава", user.id, db_session)
    assert result is not None
    assert result.system_code == "food"


async def test_guess_category_transport_keyword(db_session: AsyncSession):
    await _seed(db_session)
    user = await _make_user(db_session)

    result = await guess_category("таксі", user.id, db_session)
    assert result is not None
    assert result.system_code == "transport"


async def test_guess_category_subscription_keyword(db_session: AsyncSession):
    await _seed(db_session)
    user = await _make_user(db_session)

    result = await guess_category("netflix", user.id, db_session)
    assert result is not None
    assert result.system_code == "subscriptions"


async def test_guess_category_no_match_returns_none(db_session: AsyncSession):
    await _seed(db_session)
    user = await _make_user(db_session)

    result = await guess_category("невідоме", user.id, db_session)
    assert result is None


async def test_guess_category_none_description_returns_none(db_session: AsyncSession):
    await _seed(db_session)
    user = await _make_user(db_session)

    result = await guess_category(None, user.id, db_session)
    assert result is None


async def test_guess_category_empty_description_returns_none(db_session: AsyncSession):
    await _seed(db_session)
    user = await _make_user(db_session)

    result = await guess_category("", user.id, db_session)
    assert result is None


async def test_guess_category_substring_match(db_session: AsyncSession):
    """Token 'ресторані' should match keyword 'ресторан' via substring."""
    await _seed(db_session)
    user = await _make_user(db_session)

    result = await guess_category("ресторані", user.id, db_session)
    assert result is not None
    assert result.system_code == "food"


async def test_guess_category_case_insensitive(db_session: AsyncSession):
    await _seed(db_session)
    user = await _make_user(db_session)

    result = await guess_category("КАВА", user.id, db_session)
    assert result is not None
    assert result.system_code == "food"


# ---------------------------------------------------------------------------
# guess_category — personal categories take priority
# ---------------------------------------------------------------------------


async def test_personal_category_priority_over_system(db_session: AsyncSession):
    await _seed(db_session)
    user = await _make_user(db_session)

    personal_cat = Category(
        user_id=user.id,
        name="Моя категорія",
        emoji="🌟",
        system_code="food",
        keywords=json.dumps(["кава"], ensure_ascii=False),
    )
    db_session.add(personal_cat)
    await db_session.flush()

    result = await guess_category("кава", user.id, db_session)
    assert result is not None
    assert result.id == personal_cat.id


# ---------------------------------------------------------------------------
# add_keyword_to_user_category — creates personal copy
# ---------------------------------------------------------------------------


async def test_add_keyword_creates_personal_copy(db_session: AsyncSession):
    await _seed(db_session)
    user = await _make_user(db_session)

    cat = await add_keyword_to_user_category(user.id, "education", "курсера", db_session)

    assert cat.user_id == user.id
    assert cat.system_code == "education"
    keywords = json.loads(cat.keywords)
    assert "курсера" in keywords


async def test_add_keyword_personal_copy_includes_system_keywords(db_session: AsyncSession):
    await _seed(db_session)
    user = await _make_user(db_session)

    cat = await add_keyword_to_user_category(user.id, "education", "курсера", db_session)

    keywords = json.loads(cat.keywords)
    assert "coursera" in keywords
    assert "курсера" in keywords


async def test_add_keyword_to_existing_copy(db_session: AsyncSession):
    await _seed(db_session)
    user = await _make_user(db_session)

    await add_keyword_to_user_category(user.id, "education", "курсера", db_session)
    cat = await add_keyword_to_user_category(user.id, "education", "ворд", db_session)

    keywords = json.loads(cat.keywords)
    assert "курсера" in keywords
    assert "ворд" in keywords


async def test_add_keyword_no_duplicates(db_session: AsyncSession):
    await _seed(db_session)
    user = await _make_user(db_session)

    await add_keyword_to_user_category(user.id, "education", "курсера", db_session)
    cat = await add_keyword_to_user_category(user.id, "education", "курсера", db_session)

    keywords = json.loads(cat.keywords)
    assert keywords.count("курсера") == 1


async def test_add_keyword_normalizes_to_lowercase(db_session: AsyncSession):
    await _seed(db_session)
    user = await _make_user(db_session)

    cat = await add_keyword_to_user_category(user.id, "education", "Курсера", db_session)

    keywords = json.loads(cat.keywords)
    assert "курсера" in keywords
    assert "Курсера" not in keywords


# ---------------------------------------------------------------------------
# add_keyword_to_user_category — validation
# ---------------------------------------------------------------------------


async def test_add_keyword_too_short_raises(db_session: AsyncSession):
    await _seed(db_session)
    user = await _make_user(db_session)

    with pytest.raises(InvalidKeywordError) as exc_info:
        await add_keyword_to_user_category(user.id, "food", "до", db_session)
    assert exc_info.value.keyword == "до"


async def test_add_keyword_numeric_raises(db_session: AsyncSession):
    await _seed(db_session)
    user = await _make_user(db_session)

    with pytest.raises(InvalidKeywordError):
        await add_keyword_to_user_category(user.id, "food", "500", db_session)


async def test_add_keyword_stop_word_raises(db_session: AsyncSession):
    await _seed(db_session)
    user = await _make_user(db_session)

    with pytest.raises(InvalidKeywordError):
        await add_keyword_to_user_category(user.id, "food", "для", db_session)


async def test_add_keyword_learned_keyword_is_found_by_guess(db_session: AsyncSession):
    """After learning 'курсера' for education, guess_category should find it."""
    await _seed(db_session)
    user = await _make_user(db_session)

    await add_keyword_to_user_category(user.id, "education", "курсера", db_session)

    result = await guess_category("курсера", user.id, db_session)
    assert result is not None
    assert result.system_code == "education"
    assert result.user_id == user.id
