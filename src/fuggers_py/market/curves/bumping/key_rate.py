"""Key-rate bump helpers.

Key-rate bumps are expressed as raw decimal zero-rate shifts and applied with
a triangular profile centered on an anchor tenor.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.reference.bonds.types import Tenor
from fuggers_py.core.types import Compounding, Date

from ..term_structure import TermStructure
from ..value_type import ValueType


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _tenor_to_years(tenor: Tenor | float) -> float:
    if isinstance(tenor, Tenor):
        return float(tenor.to_years_approx())
    return float(tenor)


def _tenor_from_date(reference_date: Date, date: Date) -> float:
    return float(reference_date.days_between(date)) / 365.0


@dataclass(frozen=True, slots=True)
class KeyRateBump:
    """Localized key-rate shock on a tenor grid."""

    tenors: list[Tenor]
    key_tenor: Tenor
    bump: float

    def __post_init__(self) -> None:
        grid = [float(t.to_years_approx()) for t in self.tenors]
        if not grid:
            raise ValueError("KeyRateBump requires a non-empty tenor grid.")
        if sorted(grid) != grid:
            raise ValueError("KeyRateBump tenor grid must be sorted ascending.")
        if len(set(grid)) != len(grid):
            raise ValueError("KeyRateBump tenor grid must not contain duplicates.")
        key_years = float(self.key_tenor.to_years_approx())
        if key_years not in grid:
            raise ValueError("KeyRateBump key tenor must be part of the tenor grid.")

    def bump_at(self, tenor: Tenor | float) -> float:
        """Return the localized raw decimal bump at ``tenor``."""
        t = _tenor_to_years(tenor)
        grid = [float(x.to_years_approx()) for x in self.tenors]
        key = float(self.key_tenor.to_years_approx())
        idx = grid.index(key)

        left = grid[idx - 1] if idx - 1 >= 0 else None
        right = grid[idx + 1] if idx + 1 < len(grid) else None

        if left is None and right is None:
            return float(self.bump)
        if left is None:
            if t == key:
                return float(self.bump)
            if key <= t <= right:
                return float(self.bump) * (right - t) / (right - key)
            return 0.0
        if right is None:
            if t == key:
                return float(self.bump)
            if left <= t <= key:
                return float(self.bump) * (t - left) / (key - left)
            return 0.0

        if left <= t <= key:
            return float(self.bump) * (t - left) / (key - left)
        if key <= t <= right:
            return float(self.bump) * (right - t) / (right - key)
        return 0.0

    def apply(self, curve: TermStructure) -> "KeyRateBumpedCurve":
        """Apply the key-rate bump to a curve."""
        return KeyRateBumpedCurve(base_curve=curve, key_rate_bump=self)


@dataclass(frozen=True, slots=True)
class KeyRateBumpedCurve(TermStructure):
    """Curve with a localized key-rate zero-rate bump."""

    base_curve: TermStructure
    key_rate_bump: KeyRateBump
    _value_type = ValueType.continuous_zero()

    def date(self) -> Date:
        """Return the date of the underlying curve."""
        return self.base_curve.date()

    def bump_at_tenor(self, t: float) -> float:
        """Return the raw decimal bump applied at tenor ``t``."""
        return self.key_rate_bump.bump_at(t)

    def value_at_tenor(self, t: float) -> float:
        """Return the continuously compounded bumped zero rate at tenor ``t``."""

        tenor = max(float(t), 0.0)
        date = self.tenor_to_date(tenor)
        base_zero = self.base_curve.zero_rate(date).convert_to(Compounding.CONTINUOUS).value()
        return float(base_zero) + self.key_rate_bump.bump_at(tenor)


__all__ = ["KeyRateBump", "KeyRateBumpedCurve"]
