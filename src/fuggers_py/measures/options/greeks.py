"""Helpers for option Greeks aggregation and scaling.

Greeks are preserved in the native units returned by the pricing model:
delta and gamma per underlying unit, vega per 1.0 volatility unit, theta per
year fraction, and rho per 1.0 discount-rate change.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from fuggers_py.pricers.rates.options import OptionGreeks


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def extract_option_greeks(candidate: OptionGreeks | object) -> OptionGreeks:
    """Extract an :class:`OptionGreeks` instance from a candidate object.

    Parameters
    ----------
    candidate:
        Either an `OptionGreeks` instance or an object exposing a `.greeks`
        attribute containing one.

    Returns
    -------
    OptionGreeks
        The resolved Greek vector.
    """
    if isinstance(candidate, OptionGreeks):
        return candidate
    greeks = getattr(candidate, "greeks", None)
    if isinstance(greeks, OptionGreeks):
        return greeks
    raise TypeError("Expected OptionGreeks or an object with a `.greeks` OptionGreeks attribute.")


def scale_option_greeks(greeks: OptionGreeks | object, quantity: object) -> OptionGreeks:
    """Scale all Greeks by a position quantity.

    Returns
    -------
    OptionGreeks
        Greek vector multiplied by ``quantity``.
    """
    resolved = extract_option_greeks(greeks)
    scale = _to_decimal(quantity)
    return OptionGreeks(
        delta=resolved.delta * scale,
        gamma=resolved.gamma * scale,
        vega=resolved.vega * scale,
        theta=resolved.theta * scale,
        rho=resolved.rho * scale,
    )


def add_option_greeks(lhs: OptionGreeks | object, rhs: OptionGreeks | object) -> OptionGreeks:
    """Add two Greek vectors componentwise.

    Returns
    -------
    OptionGreeks
        Componentwise sum of the two vectors.
    """
    left = extract_option_greeks(lhs)
    right = extract_option_greeks(rhs)
    return OptionGreeks(
        delta=left.delta + right.delta,
        gamma=left.gamma + right.gamma,
        vega=left.vega + right.vega,
        theta=left.theta + right.theta,
        rho=left.rho + right.rho,
    )


def aggregate_option_greeks(items: Iterable[OptionGreeks | object]) -> OptionGreeks:
    """Aggregate an iterable of Greek vectors.

    Returns
    -------
    OptionGreeks
        Componentwise sum of all supplied vectors.
    """
    total = OptionGreeks()
    for item in items:
        total = add_option_greeks(total, item)
    return total


__all__ = ["add_option_greeks", "aggregate_option_greeks", "extract_option_greeks", "scale_option_greeks"]
