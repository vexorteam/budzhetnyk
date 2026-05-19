from decimal import Decimal

import pytest

from src.utils.formatters import format_amount


@pytest.mark.parametrize(
    "value, expected",
    [
        (Decimal("50"), "50 грн"),
        (Decimal("50.00"), "50 грн"),
        (Decimal("0"), "0 грн"),
        (Decimal("1000"), "1 000 грн"),
        (Decimal("1234567"), "1 234 567 грн"),
        (Decimal("50.50"), "50,50 грн"),
        (Decimal("1234.5"), "1 234,50 грн"),
        (Decimal("0.99"), "0,99 грн"),
        (Decimal("1000.01"), "1 000,01 грн"),
        (Decimal("9999.99"), "9 999,99 грн"),
    ],
)
def test_format_amount(value, expected):
    assert format_amount(value) == expected
