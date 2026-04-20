"""Date-based bridge helpers for the public curve tree.

These helpers translate date-based pricing code onto the tenor-based public
curve contract. The small shift helpers are used by public bond and portfolio
code that still needs date-anchored curve moves.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from decimal import Decimal

from fuggers_py._core import Tenor
from fuggers_py._core.daycounts import DayCount, DayCountConvention
from fuggers_py._core.types import Date

from .base import DiscountingCurve, RatesTermStructure

_DAY_COUNT_ALIASES = {
    "ACT/360": "ACT_360",
    "ACT/365F": "ACT_365_FIXED",
    "ACT/365FIXED": "ACT_365_FIXED",
    "ACT/365L": "ACT_365_LEAP",
    "ACT/365LEAP": "ACT_365_LEAP",
    "ACT/ACT": "ACT_ACT_ISDA",
    "ACT/ACTISDA": "ACT_ACT_ISDA",
    "ACT/ACTICMA": "ACT_ACT_ICMA",
    "ACT/ACTAFB": "ACT_ACT_AFB",
    "30/360": "THIRTY_360_US",
    "30/360US": "THIRTY_360_US",
    "30E/360": "THIRTY_360_E",
    "30/360E": "THIRTY_360_E",
    "30E/360ISDA": "THIRTY_360_E_ISDA",
    "30/360GERMAN": "THIRTY_360_GERMAN",
}

STANDARD_KEY_RATE_TENORS: tuple[Tenor, ...] = (
    Tenor.parse("6M"),
    Tenor.parse("1Y"),
    Tenor.parse("2Y"),
    Tenor.parse("3Y"),
    Tenor.parse("5Y"),
    Tenor.parse("7Y"),
    Tenor.parse("10Y"),
    Tenor.parse("20Y"),
    Tenor.parse("30Y"),
)


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _curve_day_count(curve: RatesTermStructure) -> DayCount:
    key = curve.spec.day_count.strip().upper().replace(" ", "")
    if key in DayCountConvention.__members__:
        return DayCountConvention[key].to_day_count()
    alias = _DAY_COUNT_ALIASES.get(key)
    if alias is not None:
        return DayCountConvention[alias].to_day_count()
    raise ValueError(f"Unsupported curve day-count label: {curve.spec.day_count}.")


def curve_reference_date(curve: RatesTermStructure) -> Date:
    """Return the public reference date of ``curve``."""

    return curve.reference_date


def year_fraction_from_curve(curve: RatesTermStructure, start_date: Date, end_date: Date) -> Decimal:
    """Return the curve day-count year fraction between two dates."""

    return _curve_day_count(curve).year_fraction(start_date, end_date)


def tenor_from_curve_date(curve: RatesTermStructure, date: Date) -> float:
    """Return the curve tenor in years from ``curve.reference_date`` to ``date``."""

    reference_date = curve.reference_date
    if date < reference_date:
        raise ValueError("Curve date lookup requires date >= curve.reference_date.")
    if date == reference_date:
        return 0.0
    return float(year_fraction_from_curve(curve, reference_date, date))


def discount_factor_at_date(curve: DiscountingCurve, date: Date) -> Decimal:
    """Return the discount factor at ``date`` as a raw decimal."""

    tenor = tenor_from_curve_date(curve, date)
    if tenor <= 0.0:
        return Decimal(1)
    return _to_decimal(curve.discount_factor_at(tenor))


def zero_rate_at_date(curve: DiscountingCurve, date: Date) -> Decimal:
    """Return the continuously compounded zero rate at ``date``."""

    tenor = tenor_from_curve_date(curve, date)
    if tenor <= 0.0:
        return Decimal(0)
    return _to_decimal(curve.zero_rate_at(tenor))


def forward_rate_between_dates(curve: DiscountingCurve, start_date: Date, end_date: Date) -> Decimal:
    """Return the continuously compounded forward rate between two dates."""

    start_tenor = tenor_from_curve_date(curve, start_date)
    end_tenor = tenor_from_curve_date(curve, end_date)
    if end_tenor <= start_tenor:
        raise ValueError("forward rate requires end_date > start_date.")
    return _to_decimal(curve.forward_rate_between(start_tenor, end_tenor))


def _tenor_years(value: Tenor | float | int | Decimal) -> float:
    if isinstance(value, Tenor):
        return float(value.to_years_approx())
    return float(value)


class _ShiftedDiscountingCurve:
    """Internal zero-rate shift wrapper over a public discounting curve."""

    __slots__ = ("_base_curve", "_shifted_zero_rate")

    def __init__(self, base_curve: DiscountingCurve, shifted_zero_rate) -> None:
        self._base_curve = base_curve
        self._shifted_zero_rate = shifted_zero_rate

    @property
    def spec(self):
        return self._base_curve.spec

    @property
    def reference_date(self):
        return self._base_curve.reference_date

    @property
    def rate_space(self):
        return self._base_curve.rate_space

    def max_t(self) -> float:
        return self._base_curve.max_t()

    def rate_at(self, tenor: float) -> float:
        checked_tenor = float(tenor)
        if checked_tenor <= 0.0:
            return 0.0
        return self._base_curve.zero_rate_at(checked_tenor) + float(self._shifted_zero_rate(checked_tenor))

    def discount_factor_at(self, tenor: float) -> float:
        checked_tenor = float(tenor)
        if checked_tenor <= 0.0:
            return 1.0
        shifted_zero = self.rate_at(checked_tenor)
        return math.exp(-shifted_zero * checked_tenor)

    def zero_rate_at(self, tenor: float) -> float:
        checked_tenor = float(tenor)
        if checked_tenor <= 0.0:
            raise ValueError("tenor must be > 0.")
        return self.rate_at(checked_tenor)

    def forward_rate_between(self, start_tenor: float, end_tenor: float) -> float:
        start = float(start_tenor)
        end = float(end_tenor)
        if end <= start:
            raise ValueError("end_tenor must be greater than start_tenor.")
        return math.log(self.discount_factor_at(start) / self.discount_factor_at(end)) / (end - start)


def parallel_bumped_curve(curve: DiscountingCurve, bump: float) -> DiscountingCurve:
    """Return a parallel zero-rate shift of ``curve``."""

    return _ShiftedDiscountingCurve(curve, lambda tenor: float(bump))


def key_rate_bumped_curve(
    curve: DiscountingCurve,
    *,
    tenor_grid: Sequence[Tenor | float | int | Decimal],
    key_tenor: Tenor | float | int | Decimal,
    bump: float,
) -> DiscountingCurve:
    """Return a key-rate-style zero-rate bump over ``curve``."""

    grid = sorted({_tenor_years(tenor) for tenor in tenor_grid})
    if not grid:
        raise ValueError("key_rate_bumped_curve requires a non-empty tenor grid.")
    key_years = _tenor_years(key_tenor)
    if key_years not in grid:
        grid.append(key_years)
        grid.sort()

    key_index = grid.index(key_years)
    left = None if key_index == 0 else grid[key_index - 1]
    right = None if key_index == len(grid) - 1 else grid[key_index + 1]

    def shift_at(tenor: float) -> float:
        checked_tenor = float(tenor)
        if left is None and right is None:
            return float(bump)
        if left is None:
            if checked_tenor <= key_years:
                return float(bump)
            if checked_tenor >= right:
                return 0.0
            return float(bump) * (right - checked_tenor) / (right - key_years)
        if right is None:
            if checked_tenor >= key_years:
                return float(bump)
            if checked_tenor <= left:
                return 0.0
            return float(bump) * (checked_tenor - left) / (key_years - left)
        if checked_tenor <= left or checked_tenor >= right:
            return 0.0
        if checked_tenor <= key_years:
            return float(bump) * (checked_tenor - left) / (key_years - left)
        return float(bump) * (right - checked_tenor) / (right - key_years)

    return _ShiftedDiscountingCurve(curve, shift_at)


__all__ = [
    "STANDARD_KEY_RATE_TENORS",
    "curve_reference_date",
    "discount_factor_at_date",
    "forward_rate_between_dates",
    "key_rate_bumped_curve",
    "parallel_bumped_curve",
    "tenor_from_curve_date",
    "year_fraction_from_curve",
    "zero_rate_at_date",
]
