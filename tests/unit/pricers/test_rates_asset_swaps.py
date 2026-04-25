from __future__ import annotations

from decimal import Decimal

from fuggers_py._core import PayReceive
from fuggers_py.bonds.spreads import ParParAssetSwap, ProceedsAssetSwap
from fuggers_py.bonds import FixedBondBuilder
from fuggers_py._core import YieldCalculationRules
from fuggers_py.bonds.types import ASWType
from fuggers_py._core import Currency, Date, Frequency
from fuggers_py._runtime.state import AnalyticsCurves
from fuggers_py.rates import AssetSwapPricer
from fuggers_py.rates import AssetSwap, FloatingLegSpec, ScheduleDefinition

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


def _curves(settlement: Date) -> tuple[AnalyticsCurves, object]:
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
    curves = AnalyticsCurves(
        discount_curve=base_curves.discount_curve,
        forward_curve=base_curves.forward_curve,
        repo_curve=flat_curve(settlement, Decimal("0.0310")),
        collateral_curve=flat_curve(settlement, Decimal("0.0320")),
        multicurve_environment=base_curves.multicurve_environment,
        projection_curves=base_curves.projection_curves,
    )
    return curves, term


def test_asset_swap_par_spread_matches_low_level_kernel_for_par_par() -> None:
    settlement = Date.from_ymd(2026, 1, 15)
    bond = _bond(settlement)
    curves, term_curve = _curves(settlement)
    asset_swap = AssetSwap(
        bond=bond,
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
    )

    expected = ParParAssetSwap(term_curve).calculate(bond, Decimal("101.25"), settlement)
    result = AssetSwapPricer().par_spread(asset_swap, curves)

    assert result == expected


def test_asset_swap_pv_is_zero_when_the_trade_spread_equals_proceeds_par_spread() -> None:
    settlement = Date.from_ymd(2026, 1, 15)
    bond = _bond(settlement)
    curves, term_curve = _curves(settlement)
    par_spread = ProceedsAssetSwap(term_curve).calculate(bond, Decimal("101.25"), settlement)
    asset_swap = AssetSwap(
        bond=bond,
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
        quoted_spread=par_spread,
    )

    assert AssetSwapPricer().pv(asset_swap, curves) == Decimal(0)
