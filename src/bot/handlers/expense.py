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
from src.utils.formatters import format_amount

router = Router(name="expense")


@router.message(F.text, ~F.text.startswith("/"))
async def handle_expense(message: Message, user: User, state: FSMContext) -> None:
    text = message.text or ""

    try:
        parsed = parse_expense(text)
    except ExpenseParsingError:
        await message.answer("Не зрозумів 🤔 Спробуйте: <code>Кава 50</code>")
        return

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
            await session.commit()

            amount_str = format_amount(parsed.amount)
            desc_part = f" · {parsed.description}" if parsed.description else ""
            await message.answer(
                f"✅ Додано: {amount_str} · {category.emoji} {category.name}{desc_part}"
            )
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

        keyword_added = False
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

    await callback.message.edit_text(reply)
    await callback.answer()
