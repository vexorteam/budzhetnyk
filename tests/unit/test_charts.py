import io
from datetime import datetime
from decimal import Decimal

import pytest

from src.db.models import Expense
from src.exceptions import NoDataForChartError
from src.services.charts import build_daily_bar_chart, build_pie_chart
from src.services.statistics import CategoryStat, PeriodStats


def _make_stats(by_category=None) -> PeriodStats:
    if by_category is None:
        by_category = [
            CategoryStat(1, "Їжа", "🍔", Decimal("500"), Decimal("50")),
            CategoryStat(2, "Транспорт", "🚇", Decimal("300"), Decimal("30")),
            CategoryStat(3, "Інше", "❓", Decimal("200"), Decimal("20")),
        ]
    total = sum((cs.total for cs in by_category), Decimal("0"))
    return PeriodStats(
        total=total,
        by_category=by_category,
        top_expenses=[],
        period_label="травень 2026",
    )


def _make_expense(amount: Decimal, dt: datetime) -> Expense:
    return Expense(amount=amount, created_at=dt, user_id=1, category_id=1)


# ── pie chart ────────────────────────────────────────────────────────────────


def test_pie_chart_returns_nonempty_bytesio():
    result = build_pie_chart(_make_stats())
    assert isinstance(result, io.BytesIO)
    assert len(result.read()) > 100


def test_pie_chart_empty_stats_raises():
    stats = PeriodStats(
        total=Decimal("0"),
        by_category=[],
        top_expenses=[],
        period_label="травень 2026",
    )
    with pytest.raises(NoDataForChartError):
        build_pie_chart(stats)


def test_pie_chart_single_category():
    stats = _make_stats(
        [CategoryStat(1, "Їжа", "🍔", Decimal("1000"), Decimal("100"))]
    )
    result = build_pie_chart(stats)
    assert isinstance(result, io.BytesIO)
    assert len(result.read()) > 100


def test_pie_chart_many_categories():
    cats = [
        CategoryStat(i, f"Кат {i}", "❓", Decimal("100"), Decimal("12"))
        for i in range(1, 9)
    ]
    result = build_pie_chart(_make_stats(cats))
    assert isinstance(result, io.BytesIO)
    assert len(result.read()) > 100


# ── bar chart ────────────────────────────────────────────────────────────────


def test_bar_chart_returns_nonempty_bytesio():
    expenses = [
        _make_expense(Decimal("100"), datetime(2026, 5, 1, 12, 0)),
        _make_expense(Decimal("200"), datetime(2026, 5, 2, 14, 0)),
        _make_expense(Decimal("150"), datetime(2026, 5, 3, 10, 0)),
    ]
    result = build_daily_bar_chart(expenses, "month")
    assert isinstance(result, io.BytesIO)
    assert len(result.read()) > 100


def test_bar_chart_empty_expenses_raises():
    with pytest.raises(NoDataForChartError):
        build_daily_bar_chart([], "month")


def test_bar_chart_same_day_aggregated():
    day = datetime(2026, 5, 5, 10, 0)
    expenses = [
        _make_expense(Decimal("100"), day),
        _make_expense(Decimal("200"), day),
    ]
    result = build_daily_bar_chart(expenses, "month")
    assert isinstance(result, io.BytesIO)
    assert len(result.read()) > 100


def test_bar_chart_single_expense():
    expenses = [_make_expense(Decimal("500"), datetime(2026, 5, 10, 9, 0))]
    result = build_daily_bar_chart(expenses, "month")
    assert isinstance(result, io.BytesIO)
    assert len(result.read()) > 100


def test_bar_chart_many_days():
    expenses = [
        _make_expense(Decimal("50"), datetime(2026, 5, d, 12, 0))
        for d in range(1, 29)
    ]
    result = build_daily_bar_chart(expenses, "month")
    assert isinstance(result, io.BytesIO)
    assert len(result.read()) > 100
