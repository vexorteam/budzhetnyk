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


class ExpenseParsingError(ExpenseBotError):
    def __init__(self, text: str) -> None:
        super().__init__(f"Cannot parse expense from: {text!r}")
        self.text = text


class InvalidKeywordError(ExpenseBotError):
    def __init__(self, keyword: str) -> None:
        super().__init__(f"Invalid keyword: {keyword!r}")
        self.keyword = keyword


class InvalidPeriodError(ExpenseBotError):
    def __init__(self, period: str) -> None:
        super().__init__(f"Invalid stats period: {period!r}")
        self.period = period


class ChartGenerationError(ExpenseBotError):
    def __init__(self, detail: str = "") -> None:
        msg = "Chart generation failed"
        if detail:
            msg = f"{msg}: {detail}"
        super().__init__(msg)
        self.detail = detail


class NoDataForChartError(ExpenseBotError):
    def __init__(self) -> None:
        super().__init__("No data available for chart")
