from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.db.models import Expense
    from src.services.statistics import PeriodStats


def format_amount(value: Decimal) -> str:
    if value == value.to_integral_value():
        whole = int(value)
        formatted = f"{whole:,}".replace(",", " ")
        return f"{formatted} грн"
    rounded = value.quantize(Decimal("0.01"))
    str_val = str(rounded)
    int_part, frac_part = str_val.split(".")
    int_formatted = f"{int(int_part):,}".replace(",", " ")
    return f"{int_formatted},{frac_part} грн"


def format_percent(value: Decimal) -> str:
    return f"{int(value)}%"


def format_date(dt: datetime) -> str:
    return dt.strftime("%d.%m.%Y")


def format_expense_line(expense: Expense) -> str:
    from zoneinfo import ZoneInfo

    kyiv = ZoneInfo("Europe/Kyiv")
    local_dt = expense.created_at.replace(tzinfo=ZoneInfo("UTC")).astimezone(kyiv)
    date_str = local_dt.strftime("%d.%m.%Y %H:%M")
    desc_part = f" · {expense.description}" if expense.description else ""
    return f"{date_str} · {expense.category.emoji} {expense.category.name} · {format_amount(expense.amount)}{desc_part}"


def format_stats(stats: PeriodStats, monthly_limit: Decimal | None = None) -> str:
    lines: list[str] = [f"📊 Статистика за {stats.period_label}"]

    if monthly_limit:
        lines.append(
            f"Всього: {format_amount(stats.total)} (з ліміту {format_amount(monthly_limit)})"
        )
    else:
        lines.append(f"Всього: {format_amount(stats.total)}")

    if not stats.by_category:
        lines.append("")
        lines.append("Витрат ще немає.")
        return "\n".join(lines)

    lines.append("")
    for cs in stats.by_category:
        lines.append(
            f"{cs.emoji} {cs.name} — {format_amount(cs.total)} ({format_percent(cs.percent)})"
        )

    if stats.top_expenses:
        lines.append("")
        lines.append("Топ-3 витрат:")
        for i, expense in enumerate(stats.top_expenses, 1):
            desc = expense.description or expense.category.name
            lines.append(
                f"{i}. {format_amount(expense.amount)} · {expense.category.emoji} {desc}"
            )

    return "\n".join(lines)
