"""Money-market yield helpers (`fuggers_py.bonds._yields.money_market`).

All public helpers return quoted percentage yields, not raw decimal rates.
The formulas follow the standard 360-day money-market style conventions used
by the bond analytics layer.
"""

from __future__ import annotations

from decimal import Decimal

from ..errors import AnalyticsError


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def discount_yield(face_value: object, price: object, days_to_maturity: object) -> Decimal:
    """Return a discount yield quoted as percentage points."""

    face = _to_decimal(face_value)
    px = _to_decimal(price)
    days = _to_decimal(days_to_maturity)
    if face <= 0 or px <= 0 or days <= 0:
        raise AnalyticsError.invalid_input("face, price, and days must be positive for discount yield.")
    return (face - px) / face * (Decimal(360) / days) * Decimal(100)


def bond_equivalent_yield(face_value: object, price: object, days_to_maturity: object) -> Decimal:
    """Return a bond-equivalent yield quoted as percentage points."""

    days = _to_decimal(days_to_maturity)
    if days <= 0:
        raise AnalyticsError.invalid_input("days_to_maturity must be positive for BEY.")
    disc = discount_yield(face_value, price, days)
    d = disc / Decimal(100)
    denom = Decimal(360) - d * days
    if denom == 0:
        raise AnalyticsError.invalid_input("Invalid BEY denominator (discount too large).")
    bey = (d * Decimal(365)) / denom
    return bey * Decimal(100)


def cd_equivalent_yield(face_value: object, price: object, days_to_maturity: object) -> Decimal:
    """Return a CD-equivalent yield quoted as percentage points."""

    face = _to_decimal(face_value)
    px = _to_decimal(price)
    days = _to_decimal(days_to_maturity)
    if face <= 0 or px <= 0 or days <= 0:
        raise AnalyticsError.invalid_input("face, price, and days must be positive for CD yield.")
    return (face - px) / px * (Decimal(360) / days) * Decimal(100)


def money_market_yield(face_value: object, price: object, days_to_maturity: object) -> Decimal:
    """Return the default money-market yield as quoted percentage points.

    The analytics layer currently maps the generic money-market convention to
    the bond-equivalent yield path.
    """

    return bond_equivalent_yield(face_value, price, days_to_maturity)


def money_market_yield_with_horizon(
    face_value: object,
    price: object,
    days_to_maturity: object,
    horizon_days: object,
) -> Decimal:
    """Return the money-market yield for a holding-period wrapper.

    The current implementation preserves the base money-market yield and does
    not alter the convention based on the horizon input.
    """

    _ = _to_decimal(horizon_days)
    return money_market_yield(face_value, price, days_to_maturity)


__all__ = [
    "discount_yield",
    "bond_equivalent_yield",
    "cd_equivalent_yield",
    "money_market_yield",
    "money_market_yield_with_horizon",
]
