# Budzhetnyk — Telegram-бот для обліку витрат

Персональний бот для швидкого додавання витрат, їх категоризації, перегляду статистики та експорту у Excel. Одне коротке повідомлення — одна витрата.

## Можливості

- **Швидке введення** — `Кава 50` або просто `50`
- **Розумна категоризація** — ключові слова + навчання на вашому виборі
- **Статистика** — за день, тиждень, місяць, рік
- **Графіки** — кругова діаграма і стовпчики по днях
- **Експорт у Excel** — `.xlsx` з підсумками
- **Ліміти** — щомісячний бюджет із попередженнями на 80% і 100%
- **Скасування** — `/undo` видаляє останню витрату

## Команди

| Команда | Опис |
|---------|------|
| `/start` | Реєстрація та вітання |
| `/help` | Список команд |
| `Кава 50` | Додати витрату (текст + сума) |
| `120` | Додати витрату (тільки сума, запит категорії) |
| `/stats` | Статистика за поточний місяць |
| `/stats week` | Статистика за тиждень |
| `/stats day` | Статистика за сьогодні |
| `/stats year` | Статистика за рік |
| `/chart pie` | Кругова діаграма категорій |
| `/chart bar` | Стовпчики витрат по днях |
| `/export` | Excel-файл за поточний місяць |
| `/export 2026-04` | Excel-файл за конкретний місяць |
| `/limit 10000` | Встановити місячний ліміт |
| `/limit off` | Вимкнути ліміт |
| `/limit` | Показати поточний ліміт |
| `/undo` | Видалити останню витрату (з підтвердженням) |
| `/history` | Останні 10 транзакцій |

## Технічний стек

- **Python 3.11+**
- **aiogram 3.x** — Telegram Bot API
- **SQLAlchemy 2.0** (async) + **SQLite** — база даних
- **Alembic** — міграції
- **pydantic-settings** — конфігурація
- **matplotlib** — графіки
- **openpyxl** — Excel-експорт
- **loguru** — логування

## Встановлення та запуск

### Передумови

- Python 3.11+
- Telegram Bot Token (отримати у [@BotFather](https://t.me/BotFather))

### Локально

```bash
# Клонувати репозиторій
git clone https://github.com/your-username/budzhetnyk.git
cd budzhetnyk

# Створити віртуальне оточення
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# або .venv\Scripts\activate  # Windows

# Встановити залежності
pip install -e ".[dev]"

# Налаштувати змінні середовища
cp .env.example .env
# Відредагувати .env: вписати BOT_TOKEN

# Застосувати міграції
alembic upgrade head

# Запустити бота
python -m src.main
```

### Docker

```bash
cp .env.example .env
# Відредагувати .env: вписати BOT_TOKEN

docker compose up -d
```

## Конфігурація (`.env`)

```env
BOT_TOKEN=1234567890:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DB_URL=sqlite+aiosqlite:///data/expenses.db
LOG_LEVEL=INFO
```

## Розробка

```bash
# Тести
pytest

# Тести з покриттям
pytest --cov=src --cov-report=term-missing

# Лінтер
ruff check src tests

# Форматування
black src tests
```

## Структура проекту

```
expense_bot/
├── src/
│   ├── bot/
│   │   ├── handlers/       # Telegram-хендлери
│   │   ├── keyboards/      # Inline-клавіатури
│   │   ├── middlewares/    # User та Error middleware
│   │   └── states.py       # FSM-стани
│   ├── db/
│   │   ├── models.py       # SQLAlchemy-моделі
│   │   ├── session.py      # Фабрика сесій
│   │   └── repositories/   # Репозиторії (CRUD)
│   ├── services/           # Бізнес-логіка
│   ├── utils/              # Форматери, константи
│   ├── config.py
│   ├── exceptions.py
│   └── main.py
├── migrations/             # Alembic-міграції
├── tests/
│   ├── unit/
│   └── integration/
├── data/                   # SQLite (gitignore)
└── logs/                   # Логи (gitignore)
```

## Ліцензія

MIT — детально у файлі [LICENSE](LICENSE).
