from decimal import Decimal, InvalidOperation

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.db.models import User
from src.db.repositories.user_repo import UserRepository
from src.db.session import get_session_factory
from src.exceptions import InvalidLimitError
from src.utils.formatters import format_amount

router = Router(name="limit")


@router.message(Command("limit"))
async def handle_limit(message: Message, user: User) -> None:
    text = message.text or ""
    parts = text.split(maxsplit=1)

    if len(parts) == 1:
        if user.monthly_limit:
            await message.answer(
                f"Поточний місячний ліміт: {format_amount(user.monthly_limit)}\n"
                f"Щоб змінити: <code>/limit 10000</code>\n"
                f"Щоб вимкнути: <code>/limit off</code>"
            )
        else:
            await message.answer(
                "Місячний ліміт не встановлено.\n"
                "Щоб встановити: <code>/limit 10000</code>"
            )
        return

    arg = parts[1].strip()

    if arg.lower() == "off":
        factory = get_session_factory()
        async with factory() as session:
            repo = UserRepository(session)
            await repo.set_monthly_limit(user.id, None)
            await session.commit()
        await message.answer("✅ Місячний ліміт вимкнено.")
        return

    try:
        limit = Decimal(arg.replace(",", "."))
    except InvalidOperation:
        await message.answer(
            "Невірне значення ліміту. Введіть число більше 0, наприклад: "
            "<code>/limit 10000</code>"
        )
        return

    try:
        if limit <= 0:
            raise InvalidLimitError(arg)
    except InvalidLimitError:
        await message.answer(
            "Ліміт має бути більше 0, наприклад: <code>/limit 10000</code>"
        )
        return

    factory = get_session_factory()
    async with factory() as session:
        repo = UserRepository(session)
        await repo.set_monthly_limit(user.id, limit)
        await session.commit()

    await message.answer(f"✅ Місячний ліміт встановлено: {format_amount(limit)}")
