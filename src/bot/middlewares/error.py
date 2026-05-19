from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from loguru import logger

from src.exceptions import ExpenseBotError

_ERROR_MESSAGES: dict[str, str] = {
    "NoExpenseToUndoError": "Немає витрат для скасування 🤷",
    "NoDataForChartError": "Немає даних для графіка 📭",
    "NoDataForExportError": "Немає даних для експорту 📭",
    "CategoryNotFoundError": "Категорію не знайдено ❌",
    "UserNotFoundError": "Користувача не знайдено ❌",
    "DatabaseError": "Помилка бази даних, спробуйте ще раз ⚠️",
    "ChartGenerationError": "Не вдалося побудувати графік ⚠️",
    "ExportError": "Не вдалося експортувати дані ⚠️",
    "InvalidPeriodError": "Невідомий період статистики ❌",
    "InvalidLimitError": "Невірне значення ліміту ❌",
    "ExpenseParsingError": "Не вдалося розпізнати витрату 🤔 Спробуйте: <code>Кава 50</code>",
}


class ErrorMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except ExpenseBotError as exc:
            exc_type = type(exc).__name__
            logger.warning("Domain error {}: {}", exc_type, exc)
            msg = _ERROR_MESSAGES.get(exc_type, "Сталася помилка, спробуйте ще раз ⚠️")
            await _try_reply(event, data, msg)
        except Exception as exc:
            logger.exception("Unexpected error: {}", exc)
            await _try_reply(event, data, "Сталася помилка, спробуйте ще раз 🤔")


async def _try_reply(event: TelegramObject, data: dict[str, Any], text: str) -> None:
    if not isinstance(event, Update):
        return
    chat_id: int | None = None
    if event.message:
        chat_id = event.message.chat.id
    elif event.callback_query and event.callback_query.message:
        chat_id = event.callback_query.message.chat.id

    if chat_id is None:
        return

    bot = data.get("bot")
    if bot is None:
        return

    try:
        await bot.send_message(chat_id, text)
    except Exception:
        logger.exception("Failed to send error reply to chat {}", chat_id)
