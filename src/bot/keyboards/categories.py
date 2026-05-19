from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.db.models import Category


class CategoryCallback(CallbackData, prefix="cat"):
    category_id: int


def build_categories_keyboard(categories: list[Category]) -> InlineKeyboardMarkup:
    """Build inline keyboard from categories, deduplicating by system_code (personal first)."""
    seen_codes: set[str] = set()
    unique: list[Category] = []
    for cat in categories:
        code = cat.system_code
        if code and code in seen_codes:
            continue
        if code:
            seen_codes.add(code)
        unique.append(cat)

    builder = InlineKeyboardBuilder()
    for cat in unique:
        builder.button(
            text=f"{cat.emoji} {cat.name}",
            callback_data=CategoryCallback(category_id=cat.id),
        )
    builder.adjust(3)
    return builder.as_markup()
