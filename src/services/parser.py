import re
from dataclasses import dataclass
from decimal import Decimal

from src.exceptions import ExpenseParsingError

# Matches: digits (with optional decimal separator . or ,), optional whitespace, optional currency
_AMOUNT_RE = re.compile(
    r"(\d+[.,]\d+|\d+)\s*(?:грн|uah)?",
    re.IGNORECASE,
)


@dataclass
class ParsedExpense:
    amount: Decimal
    description: str | None


def parse_expense(text: str) -> ParsedExpense:
    stripped = text.strip()
    if not stripped:
        raise ExpenseParsingError(text)

    match = _AMOUNT_RE.search(stripped)
    if match is None:
        raise ExpenseParsingError(text)

    raw_amount = match.group(1).replace(",", ".")
    amount = Decimal(raw_amount)

    before = stripped[: match.start()].strip()
    after = stripped[match.end() :].strip()
    description_parts = " ".join(p for p in (before, after) if p)
    description = description_parts if description_parts else None

    return ParsedExpense(amount=amount, description=description)
