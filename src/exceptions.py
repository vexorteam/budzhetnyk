class ExpenseBotError(Exception):
    """Base exception for all domain errors."""


class DatabaseError(ExpenseBotError):
    """Raised when a database operation fails."""


class UserNotFoundError(ExpenseBotError):
    def __init__(self, telegram_id: int) -> None:
        super().__init__(f"User with telegram_id={telegram_id} not found")
        self.telegram_id = telegram_id


class CategoryNotFoundError(ExpenseBotError):
    def __init__(self, identifier: str | int | None = None) -> None:
        msg = "Category not found"
        if identifier is not None:
            msg = f"Category not found: {identifier}"
        super().__init__(msg)
