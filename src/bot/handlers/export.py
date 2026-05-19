from datetime import datetime, timezone

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, Message

from src.db.models import User
from src.db.session import get_session_factory
from src.exceptions import NoDataForExportError
from src.services.exporter import build_excel

router = Router(name="export")


def _parse_month_arg(args: str) -> tuple[int, int] | None:
    parts = args.strip().split("-")
    if len(parts) != 2:
        return None
    try:
        year = int(parts[0])
        month = int(parts[1])
    except ValueError:
        return None
    if year < 2000 or not (1 <= month <= 12):
        return None
    return year, month


@router.message(Command("export"))
async def handle_export(
    message: Message,
    user: User,
    command: CommandObject,
) -> None:
    args = (command.args or "").strip()

    if not args:
        now = datetime.now(timezone.utc)
        year, month = now.year, now.month
    else:
        parsed = _parse_month_arg(args)
        if parsed is None:
            await message.answer(
                "Невірний формат ❌\n"
                "Приклади: <code>/export</code>, <code>/export 2026-04</code>"
            )
            return
        year, month = parsed

    factory = get_session_factory()
    async with factory() as session:
        try:
            buf = await build_excel(user.id, year, month, session)
        except NoDataForExportError:
            await message.answer(f"Немає даних за {year}-{month:02d} 📭")
            return

    filename = f"expenses_{year}-{month:02d}.xlsx"
    doc = BufferedInputFile(buf.read(), filename=filename)
    await message.answer_document(doc, caption=f"📤 Витрати за {year}-{month:02d}")
