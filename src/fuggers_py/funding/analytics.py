"""Funding analytics owned by :mod:`fuggers_py.funding`."""

from __future__ import annotations

from decimal import Decimal

from fuggers_py._core import Date, DayCountConvention

from .products import RepoTrade


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def repo_financing_cost(trade: RepoTrade) -> Decimal:
    return trade.interest_amount()


def repo_net_carry(
    trade: RepoTrade,
    *,
    collateral_income: object = Decimal(0),
    haircut_financing_cost: object = Decimal(0),
) -> Decimal:
    return _to_decimal(collateral_income) - trade.interest_amount() - _to_decimal(haircut_financing_cost)


def repo_carry_return(
    trade: RepoTrade,
    *,
    collateral_income: object = Decimal(0),
    haircut_financing_cost: object = Decimal(0),
) -> Decimal:
    cash_lent = trade.cash_lent()
    if cash_lent == Decimal(0):
        raise ValueError("repo_carry_return requires non-zero cash lent.")
    return repo_net_carry(
        trade,
        collateral_income=collateral_income,
        haircut_financing_cost=haircut_financing_cost,
    ) / cash_lent


def haircut_amount(*, collateral_value: object, haircut: object) -> Decimal:
    return _to_decimal(collateral_value) * _to_decimal(haircut)


def financed_cash(*, collateral_value: object, haircut: object) -> Decimal:
    return _to_decimal(collateral_value) - haircut_amount(collateral_value=collateral_value, haircut=haircut)


def haircut_financing_cost(
    *,
    collateral_value: object,
    haircut: object,
    funding_rate: object,
    year_fraction: object,
) -> Decimal:
    return haircut_amount(collateral_value=collateral_value, haircut=haircut) * _to_decimal(funding_rate) * _to_decimal(year_fraction)


def all_in_financing_cost(
    *,
    collateral_value: object,
    haircut: object,
    repo_rate: object,
    haircut_funding_rate: object,
    year_fraction: object,
) -> Decimal:
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
    return haircut_amount(
        collateral_value=collateral_value,
        haircut=haircut,
    ) * (_to_decimal(haircut_funding_rate) - _to_decimal(repo_rate)) * _to_decimal(year_fraction)


def futures_invoice_amount(
    *,
    futures_price: object,
    conversion_factor: object,
    accrued_at_delivery: object = Decimal(0),
    face_amount: object = Decimal(100),
) -> Decimal:
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


def specialness_spread(*, general_collateral_rate: object, specific_collateral_rate: object) -> Decimal:
    return _to_decimal(general_collateral_rate) - _to_decimal(specific_collateral_rate)


def specialness_value(
    *,
    cash_amount: object,
    general_collateral_rate: object,
    specific_collateral_rate: object,
    year_fraction: object,
) -> Decimal:
    return _to_decimal(cash_amount) * specialness_spread(
        general_collateral_rate=general_collateral_rate,
        specific_collateral_rate=specific_collateral_rate,
    ) * _to_decimal(year_fraction)


def is_special(*, general_collateral_rate: object, specific_collateral_rate: object) -> bool:
    return specialness_spread(
        general_collateral_rate=general_collateral_rate,
        specific_collateral_rate=specific_collateral_rate,
    ) > Decimal(0)


__all__ = [
    "all_in_financing_cost",
    "financed_cash",
    "futures_invoice_amount",
    "haircut_amount",
    "haircut_drag",
    "haircut_financing_cost",
    "implied_repo_rate",
    "implied_repo_rate_from_trade",
    "is_special",
    "repo_carry_return",
    "repo_financing_cost",
    "repo_net_carry",
    "specialness_spread",
    "specialness_value",
]
