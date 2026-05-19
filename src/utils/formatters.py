from decimal import Decimal


def format_amount(value: Decimal) -> str:
    if value == value.to_integral_value():
        whole = int(value)
        formatted = f"{whole:,}".replace(",", " ")
        return f"{formatted} грн"
    rounded = value.quantize(Decimal("0.01"))
    str_val = str(rounded)
    int_part, frac_part = str_val.split(".")
    int_formatted = f"{int(int_part):,}".replace(",", " ")
    return f"{int_formatted},{frac_part} грн"
