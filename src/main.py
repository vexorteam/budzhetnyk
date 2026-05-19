import asyncio
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from src.bot.handlers import expense as expense_handler
from src.bot.handlers import export as export_handler
from src.bot.handlers import history as history_handler
from src.bot.handlers import limit as limit_handler
from src.bot.handlers import start as start_handler
from src.bot.handlers import stats as stats_handler
from src.bot.handlers import undo as undo_handler
from src.bot.middlewares.error import ErrorMiddleware
from src.bot.middlewares.user import UserMiddleware
from src.config import get_settings
from src.db.repositories.category_repo import CategoryRepository
from src.db.session import get_session_factory


def _setup_logging(log_level: str) -> None:
    Path("logs").mkdir(exist_ok=True)
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
    logger.add(
        "logs/bot.log",
        level=log_level,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )


async def _heartbeat_task() -> None:
    heartbeat = Path("/tmp/heartbeat")
    while True:
        heartbeat.touch()
        await asyncio.sleep(15)


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
    dp.update.middleware(ErrorMiddleware())
    dp.update.middleware(UserMiddleware())
    dp.include_router(start_handler.router)
    dp.include_router(stats_handler.router)
    dp.include_router(export_handler.router)
    dp.include_router(limit_handler.router)
    dp.include_router(undo_handler.router)
    dp.include_router(history_handler.router)
    dp.include_router(expense_handler.router)

    await _seed_categories()
    logger.info("System categories seeded")

    heartbeat = asyncio.create_task(_heartbeat_task())
    logger.info("Polling started")
    try:
        await dp.start_polling(bot)
    finally:
        heartbeat.cancel()
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
