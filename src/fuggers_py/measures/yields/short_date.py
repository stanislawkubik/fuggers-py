"""Short-dated yield helpers (`fuggers_py.measures.yields.short_date`).

The thresholds are expressed in year fractions and are inclusive at the
boundary values.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RollForwardMethod(str, Enum):
    """Roll-forward strategy used for short-dated yield handling."""

    NONE = "NONE"
    MONOTONE = "MONOTONE"
    USE_MONEY_MARKET = "USE_MONEY_MARKET"


@dataclass(frozen=True, slots=True)
class ShortDateCalculator:
    """Determine which yield shortcut to use for a maturity bucket.

    Parameters
    ----------
    money_market_threshold : float
        Year-fraction cutoff below which money-market style quoting is used.
    short_date_threshold : float
        Year-fraction cutoff below which the instrument is treated as
        short-dated.
    """

    money_market_threshold: float = 1.0 / 12.0
    short_date_threshold: float = 1.0

    @classmethod
    def new(
        cls,
        money_market_threshold: float | None = None,
        short_date_threshold: float | None = None,
    ) -> "ShortDateCalculator":
        """Construct a calculator with optional threshold overrides."""

        return cls(
            money_market_threshold=float(money_market_threshold)
            if money_market_threshold is not None
            else 1.0 / 12.0,
            short_date_threshold=float(short_date_threshold) if short_date_threshold is not None else 1.0,
        )

    @classmethod
    def bloomberg(cls) -> "ShortDateCalculator":
        """Return the default Bloomberg-style short-date configuration."""

        return cls.new()

    def is_short_dated(self, years_to_maturity: float) -> bool:
        """Return ``True`` when maturity is at or below the short-date cutoff."""

        return float(years_to_maturity) <= float(self.short_date_threshold)

    def use_money_market_below(self, years_to_maturity: float) -> bool:
        """Return ``True`` when the money-market shortcut should apply."""

        return float(years_to_maturity) <= float(self.money_market_threshold)

    def roll_forward_method(self, years_to_maturity: float) -> RollForwardMethod:
        """Select the roll-forward strategy for the supplied maturity."""

        if self.use_money_market_below(years_to_maturity):
            return RollForwardMethod.USE_MONEY_MARKET
        if self.is_short_dated(years_to_maturity):
            return RollForwardMethod.MONOTONE
        return RollForwardMethod.NONE


__all__ = ["RollForwardMethod", "ShortDateCalculator"]
