from __future__ import annotations

from decimal import Decimal

from fuggers_py.measures.rv import CommonCurrencyFloatingBondView, usd_sofr_adjusted_rv_measure
from fuggers_py.measures.spreads import (
    BalanceSheetSpreadOverlay,
    CapitalSpreadAdjustment,
    HaircutSpreadAdjustment,
    ShadowCostSpreadAdjustment,
)
from fuggers_py.products.bonds import FixedBondBuilder
from fuggers_py.reference import YieldCalculationRules
from fuggers_py.reference.bonds.types import Tenor, ASWType
from fuggers_py.core import Currency, Date, Frequency
from fuggers_py.calc import AnalyticsCurves
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


def _overlay() -> BalanceSheetSpreadOverlay:
    return BalanceSheetSpreadOverlay(
        adjustments=(
            HaircutSpreadAdjustment(
                collateral_value=Decimal("100"),
                haircut=Decimal("0.02"),
                repo_rate=Decimal("0.0310"),
                haircut_funding_rate=Decimal("0.0450"),
                year_fraction=Decimal("0.50"),
            ),
            CapitalSpreadAdjustment(
                exposure=Decimal("100"),
                risk_weight=Decimal("0.35"),
                capital_ratio=Decimal("0.10"),
                hurdle_rate=Decimal("0.12"),
                pass_through=Decimal("0.50"),
            ),
            ShadowCostSpreadAdjustment(
                shadow_cost_rate=Decimal("0.0015"),
                utilization=Decimal("0.80"),
                pass_through=Decimal("0.75"),
            ),
        )
    )


def test_overlays_can_adjust_asset_swap_and_reference_rate_outputs_without_changing_core_pricer() -> None:
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
        asset_swap_type=ASWType.PAR_PAR,
    )
    result = AssetSwapPricer().price(asset_swap, _curves(settlement))
    overlay = _overlay()

    adjusted_funding = overlay.apply_to_funding_spread(
        base_funding_spread=result.funding_component,
        credit_spread=result.credit_component,
    )
    adjusted_reference_rate = overlay.apply(
        base_spread=result.breakdown.reference_rates.total_funding_basis,
    )

    assert adjusted_funding.base_funding_spread == result.funding_component
    assert adjusted_funding.adjusted_all_in_spread == result.par_spread + adjusted_funding.overlay_summary.total_adjustment
    assert adjusted_reference_rate.base_spread == result.breakdown.reference_rates.total_funding_basis
    assert adjusted_reference_rate.total_adjustment == adjusted_funding.overlay_summary.total_adjustment
    assert AssetSwapPricer().price(asset_swap, _curves(settlement)) == result


def test_overlays_can_adjust_global_rv_usd_sofr_measure() -> None:
    floating_view = CommonCurrencyFloatingBondView(
        instrument_id=None,
        maturity_date=Date.from_ymd(2031, 1, 15),
        source_currency=Currency.EUR,
        target_currency=Currency.USD,
        source_index_name="EURIBOR",
        source_index_tenor=Tenor.parse("6M"),
        target_index_name="SOFR",
        target_index_tenor=Tenor.parse("3M"),
        asset_swap_spread=Decimal("0.0100"),
        same_currency_basis=Decimal("0.0015"),
        cross_currency_basis=Decimal("0.0025"),
        common_currency_floating_spread=Decimal("0.0140"),
        asset_swap_result=object(),
    )
    overlay = _overlay()
    measure = usd_sofr_adjusted_rv_measure(
        floating_view,
        yardstick_spread=Decimal("0.0130"),
        adjusted_cds_spread=Decimal("0.0120"),
    )
    adjusted_measure = overlay.apply(base_spread=measure.usd_sofr_spread)

    assert adjusted_measure.base_spread == Decimal("0.0140")
    assert adjusted_measure.adjusted_spread == measure.usd_sofr_spread + adjusted_measure.total_adjustment
    assert measure.residual_to_yardstick == Decimal("0.0010")

