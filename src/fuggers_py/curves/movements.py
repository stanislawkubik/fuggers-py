"""Curve movement helpers used by discounting curve methods."""

from __future__ import annotations

import math
from bisect import bisect_left
from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal

from fuggers_py._core import Tenor

from .base import DiscountingCurve
from .errors import InvalidCurveInput

_TenorInput = Tenor | float | int | Decimal

STANDARD_KEY_RATE_TENORS: tuple[Tenor, ...] = (
    Tenor.parse("3M"),
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


def _finite_float(value: object, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise InvalidCurveInput(f"{name} must be finite.")
    return result


def _tenor_years(value: _TenorInput) -> float:
    if isinstance(value, Tenor):
        tenor = float(value.to_years_approx())
    else:
        tenor = float(value)
    if not math.isfinite(tenor) or tenor <= 0.0:
        raise InvalidCurveInput("bump tenors must be finite and > 0.")
    return tenor


class _MovedDiscountingCurve(DiscountingCurve):
    """Concrete discounting curve equal to a base curve plus a zero-rate move."""

    __slots__ = ("_base_curve", "_movement_at")

    def __init__(self, base_curve: DiscountingCurve, movement_at: Callable[[float], float]) -> None:
        super().__init__(base_curve.spec)
        self._base_curve = base_curve
        self._movement_at = movement_at

    def max_t(self) -> float:
        return self._base_curve.max_t()

    def rate_at(self, tenor: float) -> float:
        checked_tenor = _finite_float(tenor, name="tenor")
        if checked_tenor <= 0.0:
            raise InvalidCurveInput("tenor must be > 0.")
        self._check_t(checked_tenor)
        return float(self._base_curve.zero_rate_at(checked_tenor)) + float(self._movement_at(checked_tenor))

    def discount_factor_at(self, tenor: float) -> float:
        checked_tenor = _finite_float(tenor, name="tenor")
        if checked_tenor < 0.0:
            raise InvalidCurveInput("tenor must be >= 0.")
        if checked_tenor == 0.0:
            return 1.0
        self._check_t(checked_tenor)
        moved_zero_rate = self.rate_at(checked_tenor)
        return math.exp(-moved_zero_rate * checked_tenor)

    def zero_rate_at(self, tenor: float) -> float:
        return self.rate_at(tenor)


def _shifted_curve(curve: DiscountingCurve, *, shift: float) -> DiscountingCurve:
    """Return ``curve`` with every zero rate moved by ``shift``."""

    if not isinstance(curve, DiscountingCurve):
        raise InvalidCurveInput("curve must be a DiscountingCurve.")
    checked_shift = _finite_float(shift, name="shift")
    return _MovedDiscountingCurve(curve, lambda tenor: checked_shift)


def _bumped_curve(
    curve: DiscountingCurve,
    *,
    bumps: Mapping[_TenorInput, float],
    tenor_grid: Sequence[_TenorInput] | None = None,
) -> DiscountingCurve:
    """Return ``curve`` with one or more tenor-specific zero-rate bumps."""

    if not isinstance(curve, DiscountingCurve):
        raise InvalidCurveInput("curve must be a DiscountingCurve.")
    if not bumps:
        raise InvalidCurveInput("bumps must contain at least one tenor bump.")

    bump_by_tenor = {
        _tenor_years(tenor): _finite_float(bump, name="bump") for tenor, bump in bumps.items()
    }
    grid_inputs = STANDARD_KEY_RATE_TENORS if tenor_grid is None else tenor_grid
    grid = sorted({_tenor_years(tenor) for tenor in grid_inputs} | set(bump_by_tenor))
    if not grid:
        raise InvalidCurveInput("tenor_grid must contain at least one tenor.")

    movement_values = tuple(float(bump_by_tenor.get(tenor, 0.0)) for tenor in grid)

    def movement_at(tenor: float) -> float:
        checked_tenor = _finite_float(tenor, name="tenor")
        if len(grid) == 1:
            return movement_values[0]
        if checked_tenor <= grid[0]:
            return movement_values[0]
        if checked_tenor >= grid[-1]:
            return movement_values[-1]

        right_index = bisect_left(grid, checked_tenor)
        if grid[right_index] == checked_tenor:
            return movement_values[right_index]
        left_index = right_index - 1
        left_tenor = grid[left_index]
        right_tenor = grid[right_index]
        left_move = movement_values[left_index]
        right_move = movement_values[right_index]
        weight = (checked_tenor - left_tenor) / (right_tenor - left_tenor)
        return left_move + weight * (right_move - left_move)

    return _MovedDiscountingCurve(curve, movement_at)


__all__ = ["STANDARD_KEY_RATE_TENORS"]
