"""CDS-adjusted proxy risk-free helpers.

The proxy risk-free rate is inferred from a risky bond yield after removing
CDS spread adjustments plus explicit liquidity and funding components.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .adjusted_cds import adjusted_cds_breakdown


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class RiskFreeProxyBreakdown:
    """Break down the CDS-adjusted proxy risk-free rate calculation.

    Attributes
    ----------
    bond_yield:
        Input risky bond yield.
    quoted_cds_spread:
        CDS spread before adjustments.
    adjusted_cds_spread:
        CDS spread after removing non-default-risk adjustments.
    liquidity_adjustment:
        Liquidity spread component.
    funding_adjustment:
        Funding spread component.
    proxy_risk_free_rate:
        Inferred risk-free proxy rate.
    """

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
    """Infer a CDS-adjusted proxy risk-free rate from a risky bond yield.

    Returns
    -------
    RiskFreeProxyBreakdown
        Full decomposition of the proxy risk-free rate.

    Positive CDS adjustments increase the quoted spread above pure default
    risk. Positive liquidity and funding adjustments increase the risky bond
    yield above the inferred proxy risk-free rate.
    """

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
    """Return the CDS-adjusted proxy risk-free rate as a raw decimal."""

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
    "RiskFreeProxyBreakdown",
    "cds_adjusted_risk_free_rate",
    "proxy_risk_free_breakdown",
]
