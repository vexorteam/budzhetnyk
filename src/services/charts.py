import io
from collections import defaultdict
from decimal import Decimal

import matplotlib

matplotlib.use("Agg")  # non-interactive backend; must precede pyplot import
import matplotlib.pyplot as plt

from src.db.models import Expense
from src.exceptions import ChartGenerationError, NoDataForChartError
from src.services.statistics import PeriodStats

matplotlib.rcParams["font.family"] = "DejaVu Sans"


def build_pie_chart(stats: PeriodStats) -> io.BytesIO:
    if not stats.by_category:
        raise NoDataForChartError()

    try:
        labels = [
            f"{cs.name}\n{cs.percent}%" for cs in stats.by_category
        ]
        sizes = [float(cs.total) for cs in stats.by_category]

        fig, ax = plt.subplots(figsize=(8, 6))
        wedges, _ = ax.pie(sizes, startangle=90)
        ax.legend(
            wedges,
            labels,
            title="Категорії",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=9,
        )
        ax.set_title(f"Витрати: {stats.period_label}", fontsize=13, pad=16)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
        buf.seek(0)
        plt.close(fig)
        return buf
    except (OSError, ValueError, RuntimeError) as exc:
        raise ChartGenerationError(str(exc)) from exc


def build_daily_bar_chart(expenses: list[Expense], period: str) -> io.BytesIO:
    if not expenses:
        raise NoDataForChartError()

    try:
        daily: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for expense in expenses:
            day_key = expense.created_at.strftime("%d.%m")
            daily[day_key] += expense.amount

        dates = list(daily.keys())
        amounts = [float(v) for v in daily.values()]
        max_amount = max(amounts)

        fig, ax = plt.subplots(figsize=(max(8, len(dates) * 0.9), 5))
        bars = ax.bar(dates, amounts, color="#4CAF50", edgecolor="#388E3C")

        for bar, amount in zip(bars, amounts):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max_amount * 0.01,
                f"{amount:.0f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

        ax.set_xlabel("День", fontsize=11)
        ax.set_ylabel("Сума (грн)", fontsize=11)
        ax.set_title("Витрати по днях", fontsize=13)
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
        buf.seek(0)
        plt.close(fig)
        return buf
    except (OSError, ValueError, RuntimeError) as exc:
        raise ChartGenerationError(str(exc)) from exc
