"""Date-based bridge helpers for the public curve tree.

These helpers translate date-based pricing code onto the tenor-based public
curve contract.
"""

from __future__ import annotations

from decimal import Decimal

from fuggers_py._core.daycounts import DayCount
from fuggers_py._core.types import Date

from ._day_count import resolve_curve_day_count
from .base import DiscountingCurve, RatesTermStructure


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _curve_day_count(curve: RatesTermStructure) -> DayCount:
    return resolve_curve_day_count(curve.spec.day_count)


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


__all__ = [
    "curve_reference_date",
    "discount_factor_at_date",
    "forward_rate_between_dates",
    "tenor_from_curve_date",
    "year_fraction_from_curve",
    "zero_rate_at_date",
]
