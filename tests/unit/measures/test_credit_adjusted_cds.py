from __future__ import annotations

from decimal import Decimal

from fuggers_py.measures.credit import (
    adjusted_cds_breakdown,
    adjusted_cds_spread,
    cds_adjusted_risk_free_rate,
    proxy_risk_free_breakdown,
)


def test_adjusted_cds_spread_strips_parameterized_delivery_and_fx_components() -> None:
    breakdown = adjusted_cds_breakdown(
        quoted_spread=Decimal("0.0320"),
        delivery_option_adjustment=Decimal("0.0030"),
        fx_adjustment=Decimal("0.0020"),
        other_adjustment=Decimal("0.0010"),
    )

    assert breakdown.adjusted_spread == Decimal("0.0260")
    assert adjusted_cds_spread(
        quoted_spread=Decimal("0.0320"),
        delivery_option_adjustment=Decimal("0.0030"),
        fx_adjustment=Decimal("0.0020"),
        other_adjustment=Decimal("0.0010"),
    ) == Decimal("0.0260")


def test_proxy_risk_free_helper_uses_adjusted_cds_and_explicit_liquidity_inputs() -> None:
    breakdown = proxy_risk_free_breakdown(
        bond_yield=Decimal("0.0550"),
        cds_spread=Decimal("0.0200"),
        delivery_option_adjustment=Decimal("0.0020"),
        fx_adjustment=Decimal("0.0010"),
        liquidity_adjustment=Decimal("0.0005"),
        funding_adjustment=Decimal("0.0003"),
    )

    assert breakdown.adjusted_cds_spread == Decimal("0.0170")
    assert breakdown.proxy_risk_free_rate == Decimal("0.0372")
    assert cds_adjusted_risk_free_rate(
        bond_yield=Decimal("0.0550"),
        cds_spread=Decimal("0.0200"),
        delivery_option_adjustment=Decimal("0.0020"),
        fx_adjustment=Decimal("0.0010"),
        liquidity_adjustment=Decimal("0.0005"),
        funding_adjustment=Decimal("0.0003"),
    ) == Decimal("0.0372")
