"""Compounding methods for yield engines (`fuggers_py.reference.bonds.types.compounding`)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from ..errors import InvalidBondSpec


class CompoundingKind(str, Enum):
    """Compounding vocabulary used by bond yield calculations."""

    PERIODIC = "PERIODIC"
    CONTINUOUS = "CONTINUOUS"
    SIMPLE = "SIMPLE"
    DISCOUNT = "DISCOUNT"
    ACTUAL_PERIOD = "ACTUAL_PERIOD"


@dataclass(frozen=True, slots=True)
class CompoundingMethod:
    """Yield compounding rule used by pricing and risk engines."""

    kind: CompoundingKind
    frequency: int | None = None

    @classmethod
    def periodic(cls, frequency: int) -> "CompoundingMethod":
        """Create periodic compounding with the given frequency per year."""
        f = int(frequency)
        if f <= 0:
            raise InvalidBondSpec(reason="CompoundingMethod.periodic requires frequency > 0.")
        return cls(CompoundingKind.PERIODIC, frequency=f)

    @classmethod
    def actual_period(cls, frequency: int) -> "CompoundingMethod":
        """Create periodic compounding that uses actual coupon-period fractions."""
        f = int(frequency)
        if f <= 0:
            raise InvalidBondSpec(reason="CompoundingMethod.actual_period requires frequency > 0.")
        return cls(CompoundingKind.ACTUAL_PERIOD, frequency=f)

    @classmethod
    def continuous(cls) -> "CompoundingMethod":
        """Create continuously compounded yield conventions."""
        return cls(CompoundingKind.CONTINUOUS, frequency=None)

    @classmethod
    def simple(cls) -> "CompoundingMethod":
        """Create simple-interest discounting."""
        return cls(CompoundingKind.SIMPLE, frequency=None)

    @classmethod
    def discount(cls) -> "CompoundingMethod":
        """Create discount-yield discounting."""
        return cls(CompoundingKind.DISCOUNT, frequency=None)

    @classmethod
    def default(cls) -> "CompoundingMethod":
        """Return the default semi-annual bond compounding convention."""
        return cls.periodic(2)

    def discount_factor(self, yield_rate: float, t: float) -> float:
        """Return the discount factor for a raw decimal yield and year fraction."""
        y = float(yield_rate)
        tt = float(t)
        if tt == 0.0:
            return 1.0
        if self.kind in {CompoundingKind.PERIODIC, CompoundingKind.ACTUAL_PERIOD}:
            if self.frequency is None:
                raise InvalidBondSpec(reason="Periodic compounding requires frequency.")
            f = float(self.frequency)
            return (1.0 + y / f) ** (-tt * f)
        if self.kind is CompoundingKind.CONTINUOUS:
            return math.exp(-y * tt)
        if self.kind in {CompoundingKind.SIMPLE, CompoundingKind.DISCOUNT}:
            return 1.0 / (1.0 + y * tt)
        raise InvalidBondSpec(reason=f"Unknown compounding kind: {self.kind!r}.")  # pragma: no cover

    def discount_factor_derivative(self, yield_rate: float, t: float) -> float:
        """Return the first derivative of the discount factor with respect to yield."""
        y = float(yield_rate)
        tt = float(t)
        if tt == 0.0:
            return 0.0
        df = self.discount_factor(y, tt)
        if self.kind in {CompoundingKind.PERIODIC, CompoundingKind.ACTUAL_PERIOD}:
            if self.frequency is None:
                raise InvalidBondSpec(reason="Periodic compounding requires frequency.")
            f = float(self.frequency)
            return -tt * df / (1.0 + y / f)
        if self.kind is CompoundingKind.CONTINUOUS:
            return -tt * df
        if self.kind in {CompoundingKind.SIMPLE, CompoundingKind.DISCOUNT}:
            return -tt / ((1.0 + y * tt) ** 2)
        raise InvalidBondSpec(reason=f"Unknown compounding kind: {self.kind!r}.")  # pragma: no cover


__all__ = ["CompoundingMethod", "CompoundingKind"]
