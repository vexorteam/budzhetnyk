from datetime import datetime, timezone
from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from src.bot.keyboards.categories import CategoryCallback, build_categories_keyboard
from src.bot.states import ExpenseStates
from src.db.models import Category, User
from src.db.repositories.category_repo import CategoryRepository
from src.db.repositories.expense_repo import ExpenseRepository
from src.db.session import get_session_factory
from src.exceptions import ExpenseParsingError, InvalidKeywordError
from src.services.categorizer import add_keyword_to_user_category, guess_category
from src.services.parser import parse_expense
from src.services.statistics import get_limit_status
from src.utils.formatters import format_amount

router = Router(name="expense")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _limit_warning(amount_after: Decimal, limit: Decimal | None) -> str:
    status = get_limit_status(amount_after, limit)
    if status is None:
        return ""
    pct = (amount_after / limit * Decimal("100")).quantize(Decimal("1"))
    if status == "100":
        return (
            f"\n🚨 Ліміт перевищено — {format_amount(amount_after)} / {format_amount(limit)} ({pct}%)"
        )
    return (
        f"\n⚠️ Витрачено {pct}% місячного ліміту ({format_amount(amount_after)} / {format_amount(limit)})"
    )


@router.message(F.text, ~F.text.startswith("/"))
async def handle_expense(message: Message, user: User, state: FSMContext) -> None:
    text = message.text or ""

    try:
        parsed = parse_expense(text)
    except ExpenseParsingError:
        await message.answer("Не зрозумів 🤔 Спробуйте: <code>Кава 50</code>")
        return

    monthly_limit = user.monthly_limit
    factory = get_session_factory()
    async with factory() as session:
        category = await guess_category(parsed.description, user.id, session)

        if category is not None:
            repo = ExpenseRepository(session)
            await repo.create(
                user_id=user.id,
                category_id=category.id,
                amount=parsed.amount,
                description=parsed.description,
            )

            amount_after = Decimal("0")
            if monthly_limit:
                now_dt = _utcnow()
                amount_after = await repo.get_month_total(user.id, now_dt.year, now_dt.month)

            await session.commit()

            amount_str = format_amount(parsed.amount)
            desc_part = f" · {parsed.description}" if parsed.description else ""
            reply = f"✅ Додано: {amount_str} · {category.emoji} {category.name}{desc_part}"
            reply += _limit_warning(amount_after, monthly_limit)
            await message.answer(reply)
            return

        cat_repo = CategoryRepository(session)
        user_cats = await cat_repo.get_user_categories(user.id)
        system_cats = await cat_repo.get_system_categories()

    await state.set_state(ExpenseStates.waiting_for_category)
    await state.update_data(
        pending_amount=str(parsed.amount),
        pending_description=parsed.description,
    )

    keyboard = build_categories_keyboard(user_cats + system_cats)
    desc_part = f"«{parsed.description}» " if parsed.description else ""
    await message.answer(
        f"Не зміг визначити категорію для {desc_part}— оберіть вручну:",
        reply_markup=keyboard,
    )


@router.callback_query(ExpenseStates.waiting_for_category, CategoryCallback.filter())
async def handle_category_callback(
    callback: CallbackQuery,
    callback_data: CategoryCallback,
    state: FSMContext,
    user: User,
) -> None:
    fsm_data = await state.get_data()
    amount = Decimal(fsm_data["pending_amount"])
    description: str | None = fsm_data.get("pending_description")

    await state.clear()

    monthly_limit = user.monthly_limit
    amount_after = Decimal("0")
    keyword_added = False

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Category).where(Category.id == callback_data.category_id)
        )
        category = result.scalars().first()

        if category is None:
            await callback.answer("Категорія не знайдена")
            return

        repo = ExpenseRepository(session)
        await repo.create(
            user_id=user.id,
            category_id=category.id,
            amount=amount,
            description=description,
        )

        if monthly_limit:
            now_dt = _utcnow()
            amount_after = await repo.get_month_total(user.id, now_dt.year, now_dt.month)

        if description and category.system_code:
            try:
                await add_keyword_to_user_category(
                    user_id=user.id,
                    system_code=category.system_code,
                    keyword=description,
                    session=session,
                )
                keyword_added = True
            except InvalidKeywordError:
                pass

        await session.commit()

    amount_str = format_amount(amount)
    desc_part = f" · {description}" if description else ""
    reply = f"✅ Додано: {amount_str} · {category.emoji} {category.name}{desc_part}"
    if keyword_added:
        reply += f"\n🧠 Запам'ятав «{description}» для категорії {category.name}"
    reply += _limit_warning(amount_after, monthly_limit)

    await callback.message.edit_text(reply)
    await callback.answer()
