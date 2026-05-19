from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, Message

from src.db.models import User
from src.db.repositories.expense_repo import ExpenseRepository
from src.db.session import get_session_factory
from src.exceptions import InvalidPeriodError, NoDataForChartError
from src.services.charts import build_daily_bar_chart, build_pie_chart
from src.services.statistics import _get_date_range, get_period_stats
from src.utils.formatters import format_stats

router = Router(name="stats")

_VALID_PERIODS = frozenset({"day", "week", "month", "year"})
_VALID_CHART_TYPES = frozenset({"pie", "bar"})


@router.message(Command("stats"))
async def handle_stats(message: Message, user: User, command: CommandObject) -> None:
    period = (command.args or "month").strip().lower()

    if period not in _VALID_PERIODS:
        await message.answer(
            "Невідомий період ❌\n"
            "Доступні: <code>/stats</code>, <code>/stats day</code>, "
            "<code>/stats week</code>, <code>/stats year</code>"
        )
        return

    factory = get_session_factory()
    async with factory() as session:
        try:
            stats = await get_period_stats(user.id, period, session)
        except InvalidPeriodError:
            await message.answer(
                "Невідомий період ❌\n"
                "Доступні: <code>/stats</code>, <code>/stats day</code>, "
                "<code>/stats week</code>, <code>/stats year</code>"
            )
            return

    monthly_limit = user.monthly_limit if period == "month" else None
    await message.answer(format_stats(stats, monthly_limit=monthly_limit))


@router.message(Command("chart"))
async def handle_chart(message: Message, user: User, command: CommandObject) -> None:
    chart_type = (command.args or "pie").strip().lower()

    if chart_type not in _VALID_CHART_TYPES:
        await message.answer(
            "Невідомий тип графіка ❌\n"
            "Доступні: <code>/chart pie</code>, <code>/chart bar</code>"
        )
        return

    factory = get_session_factory()
    async with factory() as session:
        try:
            if chart_type == "pie":
                stats = await get_period_stats(user.id, "month", session)
                buf = build_pie_chart(stats)
                caption = f"📊 Витрати за {stats.period_label}"
            else:
                date_from, date_to = _get_date_range("month")
                repo = ExpenseRepository(session)
                expenses = await repo.get_period_expenses(user.id, date_from, date_to)
                buf = build_daily_bar_chart(expenses, "month")
                caption = "📊 Витрати по днях за поточний місяць"
        except NoDataForChartError:
            await message.answer("Немає даних для графіка 📭")
            return

    photo = BufferedInputFile(buf.read(), filename="chart.png")
    await message.answer_photo(photo, caption=caption)
