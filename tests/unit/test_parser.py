from decimal import Decimal

import pytest

from src.exceptions import ExpenseParsingError
from src.services.parser import ParsedExpense, parse_expense


def test_description_then_amount():
    result = parse_expense("Кава 50")
    assert result.amount == Decimal("50")
    assert result.description == "Кава"


def test_amount_then_description():
    result = parse_expense("50 кава")
    assert result.amount == Decimal("50")
    assert result.description == "кава"


def test_amount_only():
    result = parse_expense("50")
    assert result.amount == Decimal("50")
    assert result.description is None


def test_decimal_with_dot():
    result = parse_expense("50.5")
    assert result.amount == Decimal("50.5")
    assert result.description is None


def test_decimal_with_comma():
    result = parse_expense("50,5")
    assert result.amount == Decimal("50.5")
    assert result.description is None


def test_amount_with_hrn_spaced():
    result = parse_expense("50 грн")
    assert result.amount == Decimal("50")
    assert result.description is None


def test_amount_with_hrn_no_space():
    result = parse_expense("50грн")
    assert result.amount == Decimal("50")
    assert result.description is None


def test_amount_with_uah_lowercase():
    result = parse_expense("50 uah")
    assert result.amount == Decimal("50")
    assert result.description is None


def test_amount_with_uah_uppercase():
    result = parse_expense("50 UAH")
    assert result.amount == Decimal("50")
    assert result.description is None


def test_description_amount_currency():
    result = parse_expense("Таксі 200 грн")
    assert result.amount == Decimal("200")
    assert result.description == "Таксі"


def test_decimal_description_currency():
    result = parse_expense("кава 50,5 грн")
    assert result.amount == Decimal("50.5")
    assert result.description == "кава"


def test_large_amount():
    result = parse_expense("Оренда 1234.50 грн")
    assert result.amount == Decimal("1234.50")
    assert result.description == "Оренда"


def test_multiword_description():
    result = parse_expense("Таксі додому 150")
    assert result.amount == Decimal("150")
    assert result.description == "Таксі додому"


def test_leading_trailing_whitespace_stripped():
    result = parse_expense("  Кава 50  ")
    assert result.amount == Decimal("50")
    assert result.description == "Кава"


def test_empty_string_raises():
    with pytest.raises(ExpenseParsingError):
        parse_expense("")


def test_whitespace_only_raises():
    with pytest.raises(ExpenseParsingError):
        parse_expense("   ")


def test_text_only_raises():
    with pytest.raises(ExpenseParsingError):
        parse_expense("тільки текст без суми")


def test_exception_stores_original_text():
    text = "невалідний текст"
    with pytest.raises(ExpenseParsingError) as exc_info:
        parse_expense(text)
    assert exc_info.value.text == text


def test_exception_message_contains_text():
    text = "лише слова"
    with pytest.raises(ExpenseParsingError) as exc_info:
        parse_expense(text)
    assert text in str(exc_info.value)


def test_returns_parsed_expense_dataclass():
    result = parse_expense("Обід 100")
    assert isinstance(result, ParsedExpense)
