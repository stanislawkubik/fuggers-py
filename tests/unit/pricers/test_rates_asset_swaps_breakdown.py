from __future__ import annotations

from decimal import Decimal

from fuggers_py.measures.spreads import reference_rate_decomposition
from fuggers_py.products.bonds import FixedBondBuilder
from fuggers_py.reference import YieldCalculationRules
from fuggers_py.reference.bonds.types import ASWType
from fuggers_py.core import Currency, Date, Frequency
from fuggers_py.market.state import AnalyticsCurves
from fuggers_py.pricers.rates import AssetSwapPricer
from fuggers_py.products.rates import AssetSwap, FloatingLegSpec, PayReceive, ScheduleDefinition

from tests.helpers._rates_helpers import flat_curve, multicurve_analytics_curves, rate_index


def _bond(settlement: Date):
    return (
        FixedBondBuilder.new()
        .with_issue_date(Date.from_ymd(2021, 1, 15))
        .with_maturity_date(settlement.add_years(5))
        .with_coupon_rate(Decimal("0.0450"))
        .with_frequency(Frequency.SEMI_ANNUAL)
        .with_currency(Currency.USD)
        .with_rules(YieldCalculationRules.us_corporate())
        .build()
    )


def _curves(settlement: Date) -> AnalyticsCurves:
    discount = flat_curve(settlement, Decimal("0.0330"))
    overnight = flat_curve(settlement, Decimal("0.0340"))
    term = flat_curve(settlement, Decimal("0.0360"))
    projection_index = rate_index("TERM", "6M")
    base_curves = multicurve_analytics_curves(
        discount_curve=discount,
        discount_currency=Currency.USD,
        forward_curve=overnight,
        projection_curves={projection_index: term},
    )
    return AnalyticsCurves(
        discount_curve=base_curves.discount_curve,
        forward_curve=base_curves.forward_curve,
        repo_curve=flat_curve(settlement, Decimal("0.0310")),
        collateral_curve=flat_curve(settlement, Decimal("0.0320")),
        multicurve_environment=base_curves.multicurve_environment,
        projection_curves=base_curves.projection_curves,
    )


def test_asset_swap_breakdown_splits_funding_and_credit_components() -> None:
    settlement = Date.from_ymd(2026, 1, 15)
    asset_swap = AssetSwap(
        bond=_bond(settlement),
        settlement_date=settlement,
        floating_leg=FloatingLegSpec(
            pay_receive=PayReceive.RECEIVE,
            notional=Decimal("100"),
            index_name="TERM",
            index_tenor="6M",
            currency=Currency.USD,
            schedule=ScheduleDefinition(frequency=Frequency.QUARTERLY),
        ),
        market_dirty_price=Decimal("101.25"),
        repo_rate=Decimal("0.0100"),
        general_collateral_rate=Decimal("0.0120"),
        unsecured_overnight_rate=Decimal("0.0135"),
        term_rate=Decimal("0.0170"),
        compounding_convexity_adjustment=Decimal("0.0005"),
    )
    result = AssetSwapPricer().price(asset_swap, _curves(settlement))
    expected_reference_rates = reference_rate_decomposition(
        repo_rate=Decimal("0.0100"),
        general_collateral_rate=Decimal("0.0120"),
        unsecured_overnight_rate=Decimal("0.0135"),
        term_rate=Decimal("0.0170"),
        convexity_adjustment=Decimal("0.0005"),
    )

    assert result.funding_component == expected_reference_rates.total_funding_basis
    assert result.credit_component == result.par_spread - result.funding_component
    assert result.breakdown.reference_rates == expected_reference_rates
    assert result.breakdown.funding_component_pv + result.breakdown.credit_component_pv == result.present_value
    assert result.breakdown.effective_floating_notional == Decimal("100")


def test_asset_swap_breakdown_scales_proceeds_notional() -> None:
    settlement = Date.from_ymd(2026, 1, 15)
    asset_swap = AssetSwap(
        bond=_bond(settlement),
        settlement_date=settlement,
        floating_leg=FloatingLegSpec(
            pay_receive=PayReceive.RECEIVE,
            notional=Decimal("100"),
            index_name="TERM",
            index_tenor="6M",
            currency=Currency.USD,
            schedule=ScheduleDefinition(frequency=Frequency.QUARTERLY),
        ),
        asset_swap_type=ASWType.PROCEEDS,
        market_dirty_price=Decimal("101.25"),
    )

    result = AssetSwapPricer().price(asset_swap, _curves(settlement))

    assert result.breakdown.effective_floating_notional == Decimal("101.25")
    assert result.breakdown.spread_pv_factor > Decimal(0)
