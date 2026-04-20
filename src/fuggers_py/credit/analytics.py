"""Credit analytics helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class AdjustedCdsBreakdown:
    quoted_spread: Decimal
    delivery_option_adjustment: Decimal
    fx_adjustment: Decimal
    other_adjustment: Decimal
    adjusted_spread: Decimal


def adjusted_cds_breakdown(
    *,
    quoted_spread: object,
    delivery_option_adjustment: object = Decimal(0),
    fx_adjustment: object = Decimal(0),
    other_adjustment: object = Decimal(0),
) -> AdjustedCdsBreakdown:
    quoted = _to_decimal(quoted_spread)
    delivery = _to_decimal(delivery_option_adjustment)
    fx = _to_decimal(fx_adjustment)
    other = _to_decimal(other_adjustment)
    return AdjustedCdsBreakdown(
        quoted_spread=quoted,
        delivery_option_adjustment=delivery,
        fx_adjustment=fx,
        other_adjustment=other,
        adjusted_spread=quoted - delivery - fx - other,
    )


def adjusted_cds_spread(
    *,
    quoted_spread: object,
    delivery_option_adjustment: object = Decimal(0),
    fx_adjustment: object = Decimal(0),
    other_adjustment: object = Decimal(0),
) -> Decimal:
    return adjusted_cds_breakdown(
        quoted_spread=quoted_spread,
        delivery_option_adjustment=delivery_option_adjustment,
        fx_adjustment=fx_adjustment,
        other_adjustment=other_adjustment,
    ).adjusted_spread


@dataclass(frozen=True, slots=True)
class BondCdsBasisBreakdown:
    bond_spread: Decimal
    quoted_cds_spread: Decimal
    adjusted_cds_spread: Decimal
    delivery_option_adjustment: Decimal
    fx_adjustment: Decimal
    other_cds_adjustment: Decimal
    basis: Decimal


def bond_cds_basis_breakdown(
    *,
    bond_spread: object,
    cds_spread: object,
    delivery_option_adjustment: object = Decimal(0),
    fx_adjustment: object = Decimal(0),
    other_cds_adjustment: object = Decimal(0),
) -> BondCdsBasisBreakdown:
    bond = _to_decimal(bond_spread)
    breakdown = adjusted_cds_breakdown(
        quoted_spread=cds_spread,
        delivery_option_adjustment=delivery_option_adjustment,
        fx_adjustment=fx_adjustment,
        other_adjustment=other_cds_adjustment,
    )
    return BondCdsBasisBreakdown(
        bond_spread=bond,
        quoted_cds_spread=breakdown.quoted_spread,
        adjusted_cds_spread=breakdown.adjusted_spread,
        delivery_option_adjustment=breakdown.delivery_option_adjustment,
        fx_adjustment=breakdown.fx_adjustment,
        other_cds_adjustment=breakdown.other_adjustment,
        basis=bond - breakdown.adjusted_spread,
    )


def bond_cds_basis(
    *,
    bond_spread: object,
    cds_spread: object,
    delivery_option_adjustment: object = Decimal(0),
    fx_adjustment: object = Decimal(0),
    other_cds_adjustment: object = Decimal(0),
) -> Decimal:
    return bond_cds_basis_breakdown(
        bond_spread=bond_spread,
        cds_spread=cds_spread,
        delivery_option_adjustment=delivery_option_adjustment,
        fx_adjustment=fx_adjustment,
        other_cds_adjustment=other_cds_adjustment,
    ).basis


@dataclass(frozen=True, slots=True)
class RiskFreeProxyBreakdown:
    bond_yield: Decimal
    quoted_cds_spread: Decimal
    adjusted_cds_spread: Decimal
    liquidity_adjustment: Decimal
    funding_adjustment: Decimal
    proxy_risk_free_rate: Decimal


def proxy_risk_free_breakdown(
    *,
    bond_yield: object,
    cds_spread: object,
    delivery_option_adjustment: object = Decimal(0),
    fx_adjustment: object = Decimal(0),
    other_cds_adjustment: object = Decimal(0),
    liquidity_adjustment: object = Decimal(0),
    funding_adjustment: object = Decimal(0),
) -> RiskFreeProxyBreakdown:
    bond_yield_value = _to_decimal(bond_yield)
    liquidity = _to_decimal(liquidity_adjustment)
    funding = _to_decimal(funding_adjustment)
    breakdown = adjusted_cds_breakdown(
        quoted_spread=cds_spread,
        delivery_option_adjustment=delivery_option_adjustment,
        fx_adjustment=fx_adjustment,
        other_adjustment=other_cds_adjustment,
    )
    return RiskFreeProxyBreakdown(
        bond_yield=bond_yield_value,
        quoted_cds_spread=breakdown.quoted_spread,
        adjusted_cds_spread=breakdown.adjusted_spread,
        liquidity_adjustment=liquidity,
        funding_adjustment=funding,
        proxy_risk_free_rate=bond_yield_value - breakdown.adjusted_spread - liquidity - funding,
    )


def cds_adjusted_risk_free_rate(
    *,
    bond_yield: object,
    cds_spread: object,
    delivery_option_adjustment: object = Decimal(0),
    fx_adjustment: object = Decimal(0),
    other_cds_adjustment: object = Decimal(0),
    liquidity_adjustment: object = Decimal(0),
    funding_adjustment: object = Decimal(0),
) -> Decimal:
    return proxy_risk_free_breakdown(
        bond_yield=bond_yield,
        cds_spread=cds_spread,
        delivery_option_adjustment=delivery_option_adjustment,
        fx_adjustment=fx_adjustment,
        other_cds_adjustment=other_cds_adjustment,
        liquidity_adjustment=liquidity_adjustment,
        funding_adjustment=funding_adjustment,
    ).proxy_risk_free_rate


__all__ = [
    "AdjustedCdsBreakdown",
    "BondCdsBasisBreakdown",
    "RiskFreeProxyBreakdown",
    "adjusted_cds_breakdown",
    "adjusted_cds_spread",
    "bond_cds_basis",
    "bond_cds_basis_breakdown",
    "cds_adjusted_risk_free_rate",
    "proxy_risk_free_breakdown",
]
