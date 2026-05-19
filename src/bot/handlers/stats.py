from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from src.db.models import User
from src.db.session import get_session_factory
from src.exceptions import InvalidPeriodError
from src.services.statistics import get_period_stats
from src.utils.formatters import format_stats

router = Router(name="stats")

_VALID_PERIODS = frozenset({"day", "week", "month", "year"})


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
