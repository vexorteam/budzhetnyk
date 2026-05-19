class ExpenseBotError(Exception):
    """Base exception for all domain errors."""


class DatabaseError(ExpenseBotError):
    """Raised when a database operation fails."""
