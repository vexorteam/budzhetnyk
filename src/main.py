import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from src.bot.handlers import expense as expense_handler
from src.bot.handlers import export as export_handler
from src.bot.handlers import start as start_handler
from src.bot.handlers import stats as stats_handler
from src.bot.middlewares.user import UserMiddleware
from src.config import get_settings
from src.db.repositories.category_repo import CategoryRepository
from src.db.session import get_session_factory


def _setup_logging(log_level: str) -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        colorize=True,
    )


async def _seed_categories() -> None:
    factory = get_session_factory()
    async with factory() as session:
        repo = CategoryRepository(session)
        await repo.seed_system_categories_if_empty()
        await session.commit()


async def main() -> None:
    settings = get_settings()
    _setup_logging(settings.log_level)
    logger.info("Starting expense bot")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.update.middleware(UserMiddleware())
    dp.include_router(start_handler.router)
    dp.include_router(stats_handler.router)
    dp.include_router(export_handler.router)
    dp.include_router(expense_handler.router)

    await _seed_categories()
    logger.info("System categories seeded")

    logger.info("Polling started")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
