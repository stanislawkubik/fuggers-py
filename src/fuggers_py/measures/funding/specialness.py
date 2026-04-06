"""Specialness helpers with an explicit sign convention.

Specialness is defined as general collateral repo rate minus specific repo
rate. Positive values mean the collateral is special.
"""

from __future__ import annotations

from decimal import Decimal


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def specialness_spread(*, general_collateral_rate: object, specific_collateral_rate: object) -> Decimal:
    """Return GC minus specific repo rate.

    Positive values mean the collateral is special:
    the specific collateral finances below general collateral.
    """

    return _to_decimal(general_collateral_rate) - _to_decimal(specific_collateral_rate)


def specialness_value(
    *,
    cash_amount: object,
    general_collateral_rate: object,
    specific_collateral_rate: object,
    year_fraction: object,
) -> Decimal:
    """Return specialness value as a cash amount.

    Parameters
    ----------
    cash_amount:
        Cash balance to which the spread difference is applied.
    general_collateral_rate:
        General collateral repo rate, as a raw decimal.
    specific_collateral_rate:
        Specific collateral repo rate, as a raw decimal.
    year_fraction:
        Year fraction over which the spread accrues.
    """

    return _to_decimal(cash_amount) * specialness_spread(
        general_collateral_rate=general_collateral_rate,
        specific_collateral_rate=specific_collateral_rate,
    ) * _to_decimal(year_fraction)


def is_special(*, general_collateral_rate: object, specific_collateral_rate: object) -> bool:
    """Return ``True`` when specific collateral trades through GC."""

    return specialness_spread(
        general_collateral_rate=general_collateral_rate,
        specific_collateral_rate=specific_collateral_rate,
    ) > Decimal(0)


__all__ = [
    "is_special",
    "specialness_spread",
    "specialness_value",
]
