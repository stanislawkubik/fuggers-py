"""Short-rate model protocols for bond-option pricing."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fuggers_py.core.types import Date
from fuggers_py.market.curves import DiscountingCurve


@runtime_checkable
class ShortRateModel(Protocol):
    """Protocol for short-rate models used by the tree pricers."""

    term_structure: DiscountingCurve

    def base_forward_rate(self, start: Date, end: Date) -> float:
        """Return the base forward rate between two event dates."""
        ...

    def short_rate(self, date: Date) -> float:
        """Return the model short rate at ``date``."""
        ...

    def node_rate(self, start: Date, end: Date, *, level: int, width: int) -> float:
        """Return the short rate used at a tree node for one interval."""
        ...

    def discount(self, rate: float, dt: float, spread: float = 0.0) -> float:
        """Return the discount factor for a raw decimal rate and year fraction."""
        ...


__all__ = ["ShortRateModel"]
