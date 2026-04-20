"""Amortization schedule helpers.

The amortization helpers normalize scheduled principal reductions expressed as
absolute amounts or remaining factors.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Iterable

from fuggers_py._core.types import Date


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class AmortizationType(str, Enum):
    """Kind of principal amortization used by a bond."""

    NONE = "NONE"
    SCHEDULED_PRINCIPAL = "SCHEDULED_PRINCIPAL"
    FACTOR = "FACTOR"
    SINKING_FUND = "SINKING_FUND"


@dataclass(frozen=True, slots=True)
class AmortizationEntry:
    """One amortization step expressed as a principal amount or factor."""

    date: Date
    amount: Decimal | None = None
    factor: Decimal | None = None

    def principal_reduction(self, outstanding_notional: object) -> Decimal:
        """Return the principal reduction implied by this entry."""
        outstanding = _to_decimal(outstanding_notional)
        if self.amount is not None:
            return min(_to_decimal(self.amount), outstanding)
        if self.factor is not None:
            target = outstanding * _to_decimal(self.factor)
            return max(outstanding - target, Decimal(0))
        return Decimal(0)


@dataclass(frozen=True, slots=True)
class AmortizationSchedule:
    """Ordered amortization entries for a bond."""

    entries: tuple[AmortizationEntry, ...]
    amortization_type: AmortizationType = AmortizationType.SCHEDULED_PRINCIPAL

    @classmethod
    def new(
        cls,
        entries: Iterable[AmortizationEntry],
        *,
        amortization_type: AmortizationType = AmortizationType.SCHEDULED_PRINCIPAL,
    ) -> "AmortizationSchedule":
        """Create an amortization schedule sorted by date."""
        ordered = tuple(sorted(entries, key=lambda entry: entry.date))
        return cls(entries=ordered, amortization_type=amortization_type)

    def outstanding_notional(self, original_notional: object, *, on_date: Date | None = None) -> Decimal:
        """Return the remaining notional after applying scheduled reductions."""
        outstanding = _to_decimal(original_notional)
        for entry in self.entries:
            if on_date is not None and entry.date > on_date:
                break
            outstanding -= entry.principal_reduction(outstanding)
        return max(outstanding, Decimal(0))


__all__ = ["AmortizationEntry", "AmortizationSchedule", "AmortizationType"]
