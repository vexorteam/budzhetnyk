import json

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Category, User
from src.db.repositories.category_repo import CategoryRepository
from src.utils.constants import DEFAULT_CATEGORIES


async def test_get_system_categories_empty(db_session: AsyncSession):
    repo = CategoryRepository(db_session)
    cats = await repo.get_system_categories()
    assert cats == []


async def test_seed_system_categories_if_empty(db_session: AsyncSession):
    repo = CategoryRepository(db_session)
    await repo.seed_system_categories_if_empty()
    await db_session.commit()

    cats = await repo.get_system_categories()
    assert len(cats) == len(DEFAULT_CATEGORIES)


async def test_seed_is_idempotent(db_session: AsyncSession):
    repo = CategoryRepository(db_session)
    await repo.seed_system_categories_if_empty()
    await db_session.commit()
    await repo.seed_system_categories_if_empty()
    await db_session.commit()

    cats = await repo.get_system_categories()
    assert len(cats) == len(DEFAULT_CATEGORIES)


async def test_seeded_categories_have_correct_data(db_session: AsyncSession):
    repo = CategoryRepository(db_session)
    await repo.seed_system_categories_if_empty()
    await db_session.commit()

    cats = await repo.get_system_categories()
    codes = {c.system_code for c in cats}
    expected_codes = {d["system_code"] for d in DEFAULT_CATEGORIES}
    assert codes == expected_codes


async def test_seeded_categories_user_id_is_null(db_session: AsyncSession):
    repo = CategoryRepository(db_session)
    await repo.seed_system_categories_if_empty()
    await db_session.commit()

    cats = await repo.get_system_categories()
    assert all(c.user_id is None for c in cats)


async def test_seeded_categories_keywords_are_valid_json(db_session: AsyncSession):
    repo = CategoryRepository(db_session)
    await repo.seed_system_categories_if_empty()
    await db_session.commit()

    cats = await repo.get_system_categories()
    for cat in cats:
        keywords = json.loads(cat.keywords)
        assert isinstance(keywords, list)


async def test_get_user_categories_empty(db_session: AsyncSession):
    repo = CategoryRepository(db_session)
    cats = await repo.get_user_categories(user_id=1)
    assert cats == []


async def test_get_user_categories_returns_only_user_categories(
    db_session: AsyncSession,
):
    user = User(telegram_id=500001, username="eve")
    db_session.add(user)
    await db_session.flush()

    system_cat = Category(
        user_id=None,
        name="Їжа",
        emoji="🍔",
        system_code="food",
        keywords=json.dumps(["кава"]),
    )
    user_cat = Category(
        user_id=user.id,
        name="Їжа",
        emoji="🍔",
        system_code="food",
        keywords=json.dumps(["кава", "моя кава"]),
    )
    db_session.add(system_cat)
    db_session.add(user_cat)
    await db_session.commit()

    repo = CategoryRepository(db_session)
    user_cats = await repo.get_user_categories(user_id=user.id)
    assert len(user_cats) == 1
    assert user_cats[0].user_id == user.id

    system_cats = await repo.get_system_categories()
    assert len(system_cats) == 1
    assert system_cats[0].user_id is None


async def test_get_user_categories_does_not_return_other_user_categories(
    db_session: AsyncSession,
):
    user1 = User(telegram_id=500002, username="frank")
    user2 = User(telegram_id=500003, username="grace")
    db_session.add(user1)
    db_session.add(user2)
    await db_session.flush()

    cat1 = Category(
        user_id=user1.id,
        name="Освіта",
        emoji="📚",
        system_code="education",
        keywords=json.dumps(["курс"]),
    )
    db_session.add(cat1)
    await db_session.commit()

    repo = CategoryRepository(db_session)
    cats_user2 = await repo.get_user_categories(user_id=user2.id)
    assert cats_user2 == []
