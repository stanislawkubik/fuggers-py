"""Minimal Hull-White short-rate model support for callable bond OAS."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import exp, log, sqrt

from fuggers_py.core.types import Date
from fuggers_py.market.curves.term_structure import TermStructure

from ..errors import ModelError


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class HullWhiteModel:
    """Hull-White-style short-rate model with a flat mean-reversion tree."""

    mean_reversion: Decimal
    volatility: Decimal
    term_structure: TermStructure

    def __post_init__(self) -> None:
        object.__setattr__(self, "mean_reversion", _to_decimal(self.mean_reversion))
        object.__setattr__(self, "volatility", _to_decimal(self.volatility))
        if self.volatility < 0:
            raise ModelError(reason="HullWhiteModel volatility must be non-negative.")
        if self.mean_reversion < 0:
            raise ModelError(reason="HullWhiteModel mean_reversion must be non-negative.")

    def base_forward_rate(self, start: Date, end: Date) -> float:
        """Return the continuously compounded forward rate between dates."""
        df_start = float(self.term_structure.discount_factor(start))
        df_end = float(self.term_structure.discount_factor(end))
        dt = max(float(start.days_between(end)) / 365.0, 1e-12)
        return log(df_start / df_end) / dt

    def short_rate(self, date: Date) -> float:
        """Return the model short rate at ``date`` from the term structure."""
        ref = self.term_structure.date()
        if date <= ref:
            return 0.0
        return float(self.term_structure.zero_rate(date).value())

    def node_rate(self, start: Date, end: Date, *, level: int, width: int) -> float:
        """Return the node short rate with a mean-reverting dispersion term."""
        dt = max(float(start.days_between(end)) / 365.0, 1e-12)
        base = self.base_forward_rate(start, end)
        centered_level = level - width / 2.0
        a = float(self.mean_reversion)
        sigma = float(self.volatility)
        dispersion = centered_level * sigma * sqrt(dt) * exp(-a * dt)
        return base + dispersion

    def discount(self, rate: float, dt: float, spread: float = 0.0) -> float:
        """Return the exponential discount factor for a raw decimal rate."""
        return exp(-(rate + spread) * dt)


__all__ = ["HullWhiteModel"]
