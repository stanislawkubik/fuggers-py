"""Cash position types.

Cash positions are carried as currency amounts with an optional FX rate for
base-currency translation. The market value is the cash amount itself; there
is no clean/dirty split for cash.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.core.types import Currency


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class CashPosition:
    """A cash holding denominated in a portfolio currency.

    The amount is treated as the position's market value. The optional FX rate
    is only used when translating the cash amount into the portfolio's base
    currency.
    """

    amount: Decimal
    currency: Currency
    label: str = "cash"
    fx_rate: Decimal = Decimal(1)

    def __post_init__(self) -> None:
        """Normalize numeric inputs to :class:`~decimal.Decimal`."""

        object.__setattr__(self, "amount", _to_decimal(self.amount))
        object.__setattr__(self, "fx_rate", _to_decimal(self.fx_rate))

    def market_value(self) -> Decimal:
        """Return the cash amount as market value."""

        return self.amount

    @property
    def base_currency_value(self) -> Decimal:
        """Return the cash amount translated by ``fx_rate``."""

        return self.amount * self.fx_rate


__all__ = ["CashPosition"]
