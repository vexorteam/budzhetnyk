from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import Expense
from src.exceptions import InvalidPeriodError

PeriodType = Literal["day", "week", "month", "year"]

_VALID_PERIODS = frozenset({"day", "week", "month", "year"})

_MONTHS_UA = [
    "",
    "січень",
    "лютий",
    "березень",
    "квітень",
    "травень",
    "червень",
    "липень",
    "серпень",
    "вересень",
    "жовтень",
    "листопад",
    "грудень",
]

_MONTHS_UA_GENITIVE = [
    "",
    "січня",
    "лютого",
    "березня",
    "квітня",
    "травня",
    "червня",
    "липня",
    "серпня",
    "вересня",
    "жовтня",
    "листопада",
    "грудня",
]


@dataclass
class CategoryStat:
    category_id: int
    name: str
    emoji: str
    total: Decimal
    percent: Decimal


@dataclass
class PeriodStats:
    total: Decimal
    by_category: list[CategoryStat]
    top_expenses: list[Expense]
    period_label: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_date_range(period: PeriodType) -> tuple[datetime, datetime]:
    now = _utcnow()
    if period == "day":
        date_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
        date_to = date_from + timedelta(days=1)
    elif period == "week":
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        date_from = today_start - timedelta(days=6)
        date_to = today_start + timedelta(days=1)
    elif period == "month":
        date_from = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            date_to = datetime(now.year + 1, 1, 1, 0, 0, 0)
        else:
            date_to = datetime(now.year, now.month + 1, 1, 0, 0, 0)
    elif period == "year":
        date_from = datetime(now.year, 1, 1, 0, 0, 0)
        date_to = datetime(now.year + 1, 1, 1, 0, 0, 0)
    else:
        raise InvalidPeriodError(period)
    return date_from, date_to


def _get_period_label(period: PeriodType) -> str:
    now = _utcnow()
    if period == "day":
        return f"{now.day} {_MONTHS_UA_GENITIVE[now.month]} {now.year}"
    elif period == "week":
        return "останні 7 днів"
    elif period == "month":
        return f"{_MONTHS_UA[now.month]} {now.year}"
    elif period == "year":
        return str(now.year)
    raise InvalidPeriodError(period)


def check_limit_threshold_crossed(
    amount_before: Decimal,
    amount_after: Decimal,
    limit: Decimal | None,
) -> str | None:
    """Returns '100', '80', or None based on which threshold was first crossed."""
    if limit is None or limit <= 0:
        return None
    pct_before = amount_before / limit * Decimal("100")
    pct_after = amount_after / limit * Decimal("100")
    if pct_before < Decimal("100") <= pct_after:
        return "100"
    if pct_before < Decimal("80") <= pct_after:
        return "80"
    return None


async def get_period_stats(
    user_id: int,
    period: PeriodType,
    session: AsyncSession,
) -> PeriodStats:
    if period not in _VALID_PERIODS:
        raise InvalidPeriodError(period)

    date_from, date_to = _get_date_range(period)

    result = await session.execute(
        select(Expense)
        .options(selectinload(Expense.category))
        .where(
            Expense.user_id == user_id,
            Expense.created_at >= date_from,
            Expense.created_at < date_to,
        )
        .order_by(Expense.created_at)
    )
    expenses = list(result.scalars().all())

    if not expenses:
        return PeriodStats(
            total=Decimal("0"),
            by_category=[],
            top_expenses=[],
            period_label=_get_period_label(period),
        )

    total = sum((e.amount for e in expenses), Decimal("0"))

    # Group by system_code to merge personal and system copies of the same category.
    # Fall back to str(category_id) for categories without a system_code.
    cat_totals: dict[str, Decimal] = {}
    cat_info: dict[str, tuple[int, str, str]] = {}  # key → (id, name, emoji)

    for expense in expenses:
        cat = expense.category
        key = cat.system_code if cat.system_code else str(expense.category_id)
        cat_totals[key] = cat_totals.get(key, Decimal("0")) + expense.amount
        if key not in cat_info:
            cat_info[key] = (expense.category_id, cat.name, cat.emoji)

    by_category = sorted(
        [
            CategoryStat(
                category_id=cat_info[key][0],
                name=cat_info[key][1],
                emoji=cat_info[key][2],
                total=cat_totals[key],
                percent=(cat_totals[key] / total * 100).quantize(Decimal("1")),
            )
            for key in cat_totals
        ],
        key=lambda cs: cs.total,
        reverse=True,
    )

    top_expenses = sorted(expenses, key=lambda e: e.amount, reverse=True)[:3]

    return PeriodStats(
        total=total,
        by_category=by_category,
        top_expenses=top_expenses,
        period_label=_get_period_label(period),
    )
