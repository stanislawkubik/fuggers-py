"""Simple yield helpers (`fuggers_py._measures.yields.simple`).

The public helpers return quoted percentage simple yields. Inputs are treated
as cash coupon amounts and clean prices per 100 face.
"""

from __future__ import annotations

from decimal import Decimal

from ..errors import AnalyticsError


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def simple_yield(coupon_amount: object, clean_price: object, par: object, years: object) -> Decimal:
    """Return simple yield as a quoted percentage.

    Parameters
    ----------
    coupon_amount:
        Annual coupon payment in currency units per 100 face.
    clean_price:
        Clean price in percent of par.
    par:
        Par value, typically 100.
    years:
        Time to maturity in years.

    Returns
    -------
    Decimal
        Simple yield quoted as a percentage.
    """

    price = _to_decimal(clean_price)
    if price <= 0:
        raise AnalyticsError.invalid_input("Clean price must be positive for simple yield.")
    yrs = _to_decimal(years)
    if yrs <= 0:
        raise AnalyticsError.invalid_input("Years to maturity must be positive for simple yield.")
    coupon = _to_decimal(coupon_amount)
    par_value = _to_decimal(par)
    annualized_gain = (par_value - price) / yrs
    return (coupon + annualized_gain) / price * Decimal(100)


def simple_yield_f64(coupon_amount: float, clean_price: float, par: float, years: float) -> float:
    """Return simple yield as a float quoted percentage."""

    if clean_price <= 0:
        raise AnalyticsError.invalid_input("Clean price must be positive for simple yield.")
    if years <= 0:
        raise AnalyticsError.invalid_input("Years to maturity must be positive for simple yield.")
    annualized_gain = (float(par) - float(clean_price)) / float(years)
    return (float(coupon_amount) + annualized_gain) / float(clean_price) * 100.0


__all__ = ["simple_yield", "simple_yield_f64"]
