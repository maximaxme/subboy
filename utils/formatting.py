"""utils/formatting.py — shared price/date formatting helpers.

Centralised here so handlers and services don't each keep their own copy
(they previously drifted out of sync, e.g. the USD formatting fix).
"""
from __future__ import annotations

from decimal import Decimal

from database.models import Subscription

RU_MONTHS_NOM = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]
RU_MONTHS_GEN = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]
RU_MONTHS_SHORT = [
    "", "янв", "фев", "мар", "апр", "май", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек",
]
RU_DAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def fmt_price(price: Decimal) -> str:
    """Format a price with non-breaking thousands separators: 1 505.00"""
    integer_part = int(price)
    frac = int(round((price - integer_part) * 100))
    s = f"{integer_part:,}".replace(",", " ")
    return f"{s}.{frac:02d}"


def fmt_compact_price(price: Decimal) -> str:
    """Like fmt_price but drops a trailing .00."""
    formatted = fmt_price(price)
    return formatted[:-3] if formatted.endswith(".00") else formatted


def fmt_money(amount: Decimal, currency: str = "RUB", original: Decimal | None = None) -> str:
    """Format a money amount, showing the original currency for USD."""
    if currency == "USD" and original is not None:
        return f"${fmt_compact_price(original)} ({fmt_price(amount)} ₽)"
    return f"{fmt_price(amount)} ₽"


def fmt_subscription_price(sub: Subscription) -> str:
    return fmt_money(
        sub.price,
        getattr(sub, "price_currency", "RUB"),
        getattr(sub, "price_original", None),
    )
