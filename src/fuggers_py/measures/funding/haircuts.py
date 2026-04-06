"""Haircut financing helpers.

These helpers work with haircut fractions, collateral market values, and cash
costs. Inputs are raw decimals; outputs are currency amounts unless noted.
"""

from __future__ import annotations

from decimal import Decimal


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def haircut_amount(*, collateral_value: object, haircut: object) -> Decimal:
    """Return the haircut cash amount.

    Parameters
    ----------
    collateral_value:
        Collateral market value in currency units.
    haircut:
        Haircut fraction, expressed as a raw decimal.
    """

    return _to_decimal(collateral_value) * _to_decimal(haircut)


def financed_cash(*, collateral_value: object, haircut: object) -> Decimal:
    """Return the cash amount financed after haircut."""

    return _to_decimal(collateral_value) - haircut_amount(collateral_value=collateral_value, haircut=haircut)


def haircut_financing_cost(
    *,
    collateral_value: object,
    haircut: object,
    funding_rate: object,
    year_fraction: object,
) -> Decimal:
    """Return haircut funding cost in currency units."""

    return haircut_amount(collateral_value=collateral_value, haircut=haircut) * _to_decimal(funding_rate) * _to_decimal(year_fraction)


def all_in_financing_cost(
    *,
    collateral_value: object,
    haircut: object,
    repo_rate: object,
    haircut_funding_rate: object,
    year_fraction: object,
) -> Decimal:
    """Return total repo plus haircut funding cost in currency units."""

    return financed_cash(
        collateral_value=collateral_value,
        haircut=haircut,
    ) * _to_decimal(repo_rate) * _to_decimal(year_fraction) + haircut_financing_cost(
        collateral_value=collateral_value,
        haircut=haircut,
        funding_rate=haircut_funding_rate,
        year_fraction=year_fraction,
    )


def haircut_drag(
    *,
    collateral_value: object,
    haircut: object,
    repo_rate: object,
    haircut_funding_rate: object,
    year_fraction: object,
) -> Decimal:
    """Return the incremental cost of funding the haircut at a different rate."""

    return haircut_amount(
        collateral_value=collateral_value,
        haircut=haircut,
    ) * (_to_decimal(haircut_funding_rate) - _to_decimal(repo_rate)) * _to_decimal(year_fraction)


__all__ = [
    "all_in_financing_cost",
    "financed_cash",
    "haircut_amount",
    "haircut_drag",
    "haircut_financing_cost",
]
