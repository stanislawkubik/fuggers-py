"""Basis helpers for government bond futures.

Notes
-----
The gross basis is defined as
``cash_clean_price - futures_price * conversion_factor``.
Positive basis means the cash bond is rich to the futures contract and
negative basis means the cash bond is cheap.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class FuturesBasis:
    """Basis decomposition for a deliverable bond."""

    gross_basis: Decimal
    net_basis: Decimal
    delivery_payoff: Decimal
    financing_cost: Decimal
    coupon_income: Decimal
    delivery_option_value: Decimal


def gross_basis(futures_price: object, conversion_factor: object, clean_price: object) -> Decimal:
    """Return the gross basis in percent of par."""
    return _to_decimal(clean_price) - _to_decimal(futures_price) * _to_decimal(conversion_factor)


def net_basis(
    futures_price: object,
    conversion_factor: object,
    clean_price: object,
    *,
    financing_cost: object = Decimal(0),
    coupon_income: object = Decimal(0),
    delivery_option_value: object = Decimal(0),
) -> Decimal:
    """Return the net basis after financing, carry, and delivery-option terms."""
    gross = gross_basis(futures_price, conversion_factor, clean_price)
    return gross + _to_decimal(financing_cost) - _to_decimal(coupon_income) - _to_decimal(delivery_option_value)


def basis_metrics(
    futures_price: object,
    conversion_factor: object,
    clean_price: object,
    *,
    financing_cost: object = Decimal(0),
    coupon_income: object = Decimal(0),
    delivery_option_value: object = Decimal(0),
) -> FuturesBasis:
    """Return gross basis, net basis, and component cash-flow metrics."""
    gross = gross_basis(futures_price, conversion_factor, clean_price)
    delivery = -gross
    return FuturesBasis(
        gross_basis=gross,
        net_basis=net_basis(
            futures_price,
            conversion_factor,
            clean_price,
            financing_cost=financing_cost,
            coupon_income=coupon_income,
            delivery_option_value=delivery_option_value,
        ),
        delivery_payoff=delivery,
        financing_cost=_to_decimal(financing_cost),
        coupon_income=_to_decimal(coupon_income),
        delivery_option_value=_to_decimal(delivery_option_value),
    )


__all__ = ["FuturesBasis", "basis_metrics", "gross_basis", "net_basis"]
