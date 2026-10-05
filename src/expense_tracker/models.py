from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

_AMOUNT_RE = re.compile(r"\d+(\.\d{1,2})?")
_CATEGORY_RE = re.compile(r"[a-z0-9]+(?:[-_ ][a-z0-9]+)*")


class InvalidAmount(ValueError):
    pass


class InvalidCategory(ValueError):
    pass


def parse_cents(amount: str) -> int:
    text = amount.strip()
    if not _AMOUNT_RE.fullmatch(text):
        raise InvalidAmount(f"amount must be a positive number with at most 2 decimals: {amount!r}")
    whole, _, fraction = text.partition(".")
    cents = int(whole) * 100 + int(fraction.ljust(2, "0") or 0)
    if cents <= 0:
        raise InvalidAmount(f"amount must be greater than zero: {amount!r}")
    return cents


@dataclass(frozen=True, slots=True)
class Expense:
    amount: str
    category: str
    spent_on: date
    cents: int = field(init=False, default=0)
    id: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "cents", parse_cents(self.amount))
        object.__setattr__(self, "category", normalize_category(self.category))

    @property
    def formatted_amount(self) -> str:
        return f"{self.cents // 100}.{self.cents % 100:02d}"


def normalize_category(category: str) -> str:
    normalized = category.strip().lower()
    if not _CATEGORY_RE.fullmatch(normalized):
        raise InvalidCategory(f"category must be alphanumeric with - or _ inside: {category!r}")
    return normalized
