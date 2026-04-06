"""Implied-repo analytics from futures and cash-bond primitives.

The helpers return raw decimal repo rates and cash invoice amounts. Repo rates
are annualized decimals, not percentages.
"""

from __future__ import annotations

from decimal import Decimal

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Date
from fuggers_py.products.funding import RepoTrade


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def futures_invoice_amount(
    *,
    futures_price: object,
    conversion_factor: object,
    accrued_at_delivery: object = Decimal(0),
    face_amount: object = Decimal(100),
) -> Decimal:
    """Return the futures invoice amount in currency units.

    Parameters
    ----------
    futures_price:
        Futures price quoted in percent of par.
    conversion_factor:
        Futures conversion factor.
    accrued_at_delivery:
        Bond accrued interest at delivery in currency units.
    face_amount:
        Bond face amount.
    """

    face = _to_decimal(face_amount)
    invoice_price = _to_decimal(futures_price) * _to_decimal(conversion_factor) + _to_decimal(accrued_at_delivery)
    return face * invoice_price / Decimal(100)


def implied_repo_rate(
    *,
    spot_price: object,
    futures_price: object,
    conversion_factor: object,
    start_date: Date,
    end_date: Date,
    coupon_income: object = Decimal(0),
    accrued_on_purchase: object = Decimal(0),
    accrued_at_delivery: object = Decimal(0),
    face_amount: object = Decimal(100),
    day_count_convention: DayCountConvention = DayCountConvention.ACT_360,
) -> Decimal:
    """Return the annualized implied repo rate as a raw decimal.

    Parameters
    ----------
    spot_price:
        Cash-bond clean price in percent of par.
    futures_price:
        Futures price quoted in percent of par.
    conversion_factor:
        Futures conversion factor.
    start_date, end_date:
        Repo start and end dates.
    coupon_income:
        Coupon income earned over the financing window, in percent of par.
    accrued_on_purchase:
        Accrued interest paid when purchasing the bond, in percent of par.
    accrued_at_delivery:
        Accrued interest embedded in the futures invoice at delivery, in
        currency units.
    face_amount:
        Bond face amount.
    day_count_convention:
        Convention used to annualize the financing period.
    """

    tau = day_count_convention.to_day_count().year_fraction(start_date, end_date)
    if tau == Decimal(0):
        raise ValueError("implied_repo_rate requires distinct start and end dates.")

    face = _to_decimal(face_amount)
    purchase_amount = face * (_to_decimal(spot_price) + _to_decimal(accrued_on_purchase)) / Decimal(100)
    if purchase_amount == Decimal(0):
        raise ValueError("implied_repo_rate requires a non-zero purchase amount.")

    delivery_amount = futures_invoice_amount(
        futures_price=futures_price,
        conversion_factor=conversion_factor,
        accrued_at_delivery=accrued_at_delivery,
        face_amount=face,
    ) + face * _to_decimal(coupon_income) / Decimal(100)
    return (delivery_amount / purchase_amount - Decimal(1)) / tau


def implied_repo_rate_from_trade(
    trade: RepoTrade,
    *,
    futures_price: object,
    conversion_factor: object,
    coupon_income: object = Decimal(0),
    accrued_on_purchase: object = Decimal(0),
    accrued_at_delivery: object = Decimal(0),
) -> Decimal:
    """Return the implied repo rate using repo-trade dates and day count."""

    face_amount = trade.notional if trade.notional is not None else Decimal(100)
    return implied_repo_rate(
        spot_price=trade.collateral_price,
        futures_price=futures_price,
        conversion_factor=conversion_factor,
        start_date=trade.start_date,
        end_date=trade.end_date,
        coupon_income=coupon_income,
        accrued_on_purchase=accrued_on_purchase,
        accrued_at_delivery=accrued_at_delivery,
        face_amount=face_amount,
        day_count_convention=trade.day_count_convention,
    )


__all__ = [
    "futures_invoice_amount",
    "implied_repo_rate",
    "implied_repo_rate_from_trade",
]
