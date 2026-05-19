# Участь у розробці

Дякуємо за інтерес до проекту! Нижче — правила та інструкції для учасників.

## Кодекс поведінки

Будьте ввічливими у спілкуванні. Конструктивна критика вітається, образи — ні.

## Як повідомити про баг

1. Перевірте [Issues](https://github.com/your-username/budzhetnyk/issues) — можливо, вже відкрито.
2. Відкрийте новий Issue з шаблоном "Bug report":
   - версія Python і ОС
   - кроки для відтворення
   - очікувана поведінка
   - фактична поведінка
   - логи (без `BOT_TOKEN` та чутливих даних)

## Як запропонувати функціонал

Відкрийте Issue з шаблоном "Feature request". Опишіть сценарій використання та мотивацію.

## Процес розробки

### Гілки

| Тип | Назва |
|-----|-------|
| Функціонал | `feat/short-description` |
| Виправлення | `fix/short-description` |
| Рефакторинг | `refactor/short-description` |
| Документація | `docs/short-description` |

### Комміти (Conventional Commits)

```
feat(parser): add support for UAH suffix
fix(categorizer): handle empty description
docs(readme): add docker instructions
test(exporter): add edge case for empty month
refactor(stats): extract period calculation
```

Типи: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`.

### Pull Request

1. Fork репозиторію.
2. Створіть гілку від `main`.
3. Внесіть зміни, дотримуючись правил нижче.
4. Переконайтесь, що всі тести проходять: `pytest`.
5. Запустіть лінтер: `ruff check src tests`.
6. Відформатуйте код: `black src tests`.
7. Відкрийте PR з описом змін і посиланням на Issue.

## Правила коду

### Загальні

- Python 3.11+, підтримка async/await скрізь, де є I/O.
- Гроші — тільки `Decimal`, ніколи `float`.
- Всі дати в БД — UTC; конвертація в `Europe/Kyiv` тільки при відображенні.
- Кастомні винятки з `src/exceptions.py`, жодних голих `raise Exception`.

### Тести

- Новий функціонал = нові тести. PR без тестів не мержиться.
- Сервіси та репозиторії — юніт-тести.
- Хендлери — інтеграційні тести.
- `pytest` повинен бути зеленим.

### Структура

Дотримуйтесь структури з `CLAUDE.md` (розділ 4). Не створюйте нових модулів без обговорення.

### База даних

- Зміна моделі = нова Alembic-міграція. Ніколи не правте існуючі міграції.
- Тестові БД — in-memory SQLite через pytest-фікстуру.

## Локальне середовище

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Заповнити .env
alembic upgrade head
pytest
```

## Питання

Відкрийте [Discussion](https://github.com/your-username/budzhetnyk/discussions) або Issue з тегом `question`.
