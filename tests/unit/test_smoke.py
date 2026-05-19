import importlib


def test_import_main():
    """Importing src.main must not raise."""
    importlib.import_module("src.main")


def test_settings_reads_from_env():
    from src.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    assert settings.bot_token == "0:test_token_for_pytest"
    assert settings.db_url == "sqlite+aiosqlite:///:memory:"


def test_expense_bot_error_is_exception():
    from src.exceptions import ExpenseBotError

    err = ExpenseBotError("test")
    assert isinstance(err, Exception)
    assert str(err) == "test"
