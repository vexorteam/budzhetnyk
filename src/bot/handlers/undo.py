from aiogram import Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.db.models import Expense, User
from src.db.repositories.expense_repo import ExpenseRepository
from src.db.session import get_session_factory
from src.exceptions import NoExpenseToUndoError
from src.utils.formatters import format_amount

router = Router(name="undo")


class UndoCallback(CallbackData, prefix="undo"):
    action: str
    expense_id: int


def _build_undo_keyboard(expense_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Так, видалити",
                    callback_data=UndoCallback(
                        action="confirm", expense_id=expense_id
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="Скасувати",
                    callback_data=UndoCallback(
                        action="cancel", expense_id=expense_id
                    ).pack(),
                ),
            ]
        ]
    )


def _format_expense_preview(expense: Expense) -> str:
    desc_part = f" · {expense.description}" if expense.description else ""
    date_str = expense.created_at.strftime("%d.%m.%Y %H:%M")
    return (
        f"{format_amount(expense.amount)} · {expense.category.emoji} {expense.category.name}{desc_part}\n"
        f"📅 {date_str}"
    )


@router.message(Command("undo"))
async def handle_undo(message: Message, user: User) -> None:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Expense)
            .options(selectinload(Expense.category))
            .where(Expense.user_id == user.id)
            .order_by(Expense.created_at.desc(), Expense.id.desc())
            .limit(1)
        )
        expense = result.scalars().first()

    if expense is None:
        raise NoExpenseToUndoError()

    await message.answer(
        f"🗑 Видалити останню витрату?\n\n{_format_expense_preview(expense)}",
        reply_markup=_build_undo_keyboard(expense.id),
    )


@router.callback_query(UndoCallback.filter())
async def handle_undo_callback(
    callback: CallbackQuery,
    callback_data: UndoCallback,
    user: User,
) -> None:
    if callback_data.action == "cancel":
        await callback.message.edit_text("Скасовано.")
        await callback.answer()
        return

    factory = get_session_factory()
    async with factory() as session:
        repo = ExpenseRepository(session)
        await repo.delete(callback_data.expense_id)
        await session.commit()

    await callback.message.edit_text("✅ Видалено.")
    await callback.answer()
