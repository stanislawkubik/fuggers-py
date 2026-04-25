"""True yield helpers (`fuggers_py.bonds._yields.true_yield`).

True yield is represented as a raw decimal rate. The helper adds the supplied
settlement adjustment directly to the street yield.
"""

from __future__ import annotations

from decimal import Decimal


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def settlement_adjustment(value: object | None = None) -> Decimal:
    """Return a settlement adjustment term.

    The adjustment defaults to zero unless supplied by the caller.
    """

    if value is None:
        return Decimal(0)
    return _to_decimal(value)


def true_yield(street_yield: object, settlement_adjustment_value: object) -> Decimal:
    """Return true yield as a raw decimal rate.

    True yield is modeled as street yield plus the supplied settlement
    adjustment.
    """

    return _to_decimal(street_yield) + _to_decimal(settlement_adjustment_value)


__all__ = ["true_yield", "settlement_adjustment"]
