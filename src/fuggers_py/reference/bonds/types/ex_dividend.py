"""Ex-dividend rules (`fuggers_py.reference.bonds.types.ex_dividend`)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExDividendRules:
    """Number of days before coupon payment when the bond trades ex-dividend."""

    ex_dividend_days: int = 0

    @classmethod
    def none(cls) -> "ExDividendRules":
        """Return a convention with no ex-dividend period."""
        return cls(ex_dividend_days=0)

    @classmethod
    def uk_gilt(cls) -> "ExDividendRules":
        """Return the standard UK gilt seven-day ex-dividend convention."""
        return cls(ex_dividend_days=7)


__all__ = ["ExDividendRules"]
