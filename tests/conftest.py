import os

# Must be set before any module that triggers Settings() initialisation is imported.
os.environ.setdefault("BOT_TOKEN", "0:test_token_for_pytest")
os.environ.setdefault("DB_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("LOG_LEVEL", "WARNING")
