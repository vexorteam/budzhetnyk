import json
import re

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Category
from src.db.repositories.category_repo import CategoryRepository
from src.exceptions import InvalidKeywordError
from src.utils.constants import STOP_WORDS

_PUNCT_RE = re.compile(r"[^\w\s]")


def _normalize_tokens(text: str) -> list[str]:
    text = text.lower()
    text = _PUNCT_RE.sub(" ", text)
    return [t for t in text.split() if t]


def _is_numeric(s: str) -> bool:
    return s.replace(".", "").replace(",", "").isdigit()


def _matches(tokens: list[str], keywords: list[str]) -> bool:
    for token in tokens:
        for kw in keywords:
            if kw in token or token in kw:
                return True
    return False


async def guess_category(
    description: str | None,
    user_id: int,
    session: AsyncSession,
) -> Category | None:
    if not description:
        return None

    tokens = _normalize_tokens(description)
    if not tokens:
        return None

    cat_repo = CategoryRepository(session)

    for cat in await cat_repo.get_user_categories(user_id):
        keywords: list[str] = json.loads(cat.keywords)
        if _matches(tokens, keywords):
            return cat

    for cat in await cat_repo.get_system_categories():
        keywords = json.loads(cat.keywords)
        if _matches(tokens, keywords):
            return cat

    return None


async def add_keyword_to_user_category(
    user_id: int,
    system_code: str,
    keyword: str,
    session: AsyncSession,
) -> Category:
    keyword = keyword.lower().strip()

    if len(keyword) < 3:
        raise InvalidKeywordError(keyword)
    if _is_numeric(keyword):
        raise InvalidKeywordError(keyword)
    if keyword in STOP_WORDS:
        raise InvalidKeywordError(keyword)

    cat_repo = CategoryRepository(session)

    user_cats = await cat_repo.get_user_categories(user_id)
    user_cat = next((c for c in user_cats if c.system_code == system_code), None)

    if user_cat is None:
        system_cats = await cat_repo.get_system_categories()
        system_cat = next(
            (c for c in system_cats if c.system_code == system_code), None
        )

        base_keywords: list[str] = json.loads(system_cat.keywords) if system_cat else []
        if keyword not in base_keywords:
            base_keywords = base_keywords + [keyword]

        user_cat = Category(
            user_id=user_id,
            name=system_cat.name if system_cat else system_code,
            emoji=system_cat.emoji if system_cat else "❓",
            system_code=system_code,
            keywords=json.dumps(base_keywords, ensure_ascii=False),
        )
        session.add(user_cat)
        await session.flush()
    else:
        existing: list[str] = json.loads(user_cat.keywords)
        if keyword not in existing:
            existing.append(keyword)
            user_cat.keywords = json.dumps(existing, ensure_ascii=False)
            await session.flush()

    return user_cat
