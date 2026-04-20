"""Shared ex-dividend rules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExDividendRules:
    """Number of days before coupon payment when a bond trades ex-dividend."""

    ex_dividend_days: int = 0

    @classmethod
    def none(cls) -> "ExDividendRules":
        return cls(ex_dividend_days=0)

    @classmethod
    def uk_gilt(cls) -> "ExDividendRules":
        return cls(ex_dividend_days=7)


__all__ = ["ExDividendRules"]
