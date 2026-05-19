from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.db.models import User

router = Router(name="start")

_HELP_TEXT = (
    "<b>Як користуватись:</b>\n\n"
    "<b>Додавання витрати:</b>\n"
    "  <code>Кава 50</code> — опис і сума\n"
    "  <code>120</code> — тільки сума (запитаю категорію)\n\n"
    "<b>Статистика:</b>\n"
    "  /stats — поточний місяць\n"
    "  /stats week — тиждень\n"
    "  /stats day — сьогодні\n"
    "  /stats year — рік\n\n"
    "<b>Графіки:</b>\n"
    "  /chart pie — кругова діаграма\n"
    "  /chart bar — по днях\n\n"
    "<b>Експорт і управління:</b>\n"
    "  /export — Excel за поточний місяць\n"
    "  /export 2026-04 — Excel за конкретний місяць\n"
    "  /limit 10000 — встановити місячний ліміт\n"
    "  /limit off — вимкнути ліміт\n"
    "  /undo — видалити останню витрату\n"
    "  /history — останні 10 записів\n"
    "  /help — ця підказка"
)


@router.message(Command("start"))
async def cmd_start(message: Message, user: User) -> None:
    name = message.from_user.first_name if message.from_user else "друже"
    await message.answer(
        f"Привіт, {name}! 👋\n\n"
        "Я допоможу вести облік витрат прямо в Telegram.\n"
        "Просто напиши <code>Кава 50</code> — і я все збережу.\n\n" + _HELP_TEXT
    )


@router.message(Command("help"))
async def cmd_help(message: Message, user: User) -> None:
    await message.answer(_HELP_TEXT)
