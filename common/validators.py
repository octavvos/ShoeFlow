from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

phone_validator = RegexValidator(
    r"^\+998\d{9}$", "Telefon raqam +998XXXXXXXXX formatida bo'lishi kerak."
)
inn_validator = RegexValidator(r"^\d{9}$", "STIR (INN) 9 ta raqamdan iborat bo'lishi kerak.")


def ean13_check_digit(first12: str) -> str:
    """EAN-13 shtrix-kodning nazorat raqamini hisoblaydi."""
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(first12))
    return str((10 - total % 10) % 10)


def validate_ean13(value: str) -> None:
    if len(value) != 13 or not value.isdigit():
        raise ValidationError("Shtrix-kod 13 ta raqamdan iborat bo'lishi kerak.")
    if ean13_check_digit(value[:12]) != value[12]:
        raise ValidationError("Shtrix-kodning nazorat raqami noto'g'ri.")
