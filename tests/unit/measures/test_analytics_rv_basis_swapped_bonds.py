from __future__ import annotations

from decimal import Decimal

from fuggers_py.measures.rv import bond_to_common_currency_fixed, bond_to_common_currency_floating
from fuggers_py.products.bonds import FixedBondBuilder
from fuggers_py.reference import YieldCalculationRules
from fuggers_py.core import Currency, Date, Frequency
from fuggers_py.market.curves import MultiCurveEnvironmentBuilder
from fuggers_py.calc import AnalyticsCurves
from fuggers_py.pricers.rates import AssetSwapPricer, BasisSwapPricer, CrossCurrencyBasisSwapPricer
from fuggers_py.products.rates import (
    AssetSwap,
    BasisSwap,
    CrossCurrencyBasisSwap,
    FloatingLegSpec,
    PayReceive,
    ScheduleDefinition,
)

from tests.helpers._rates_helpers import flat_curve, rate_index


def _bond(settlement: Date):
    return (
        FixedBondBuilder.new()
        .with_issue_date(Date.from_ymd(2021, 1, 15))
        .with_maturity_date(settlement.add_years(5))
        .with_coupon_rate(Decimal("0.0325"))
        .with_frequency(Frequency.SEMI_ANNUAL)
        .with_currency(Currency.EUR)
        .with_rules(YieldCalculationRules.us_corporate())
        .build()
    )


def _curves(reference_date: Date) -> AnalyticsCurves:
    eur_discount_curve = flat_curve(reference_date, "0.0200")
    usd_discount_curve = flat_curve(reference_date, "0.0300")
    eur_term_6m_curve = flat_curve(reference_date, "0.0240")
    eur_term_3m_curve = flat_curve(reference_date, "0.0225")
    usd_sofr_curve = flat_curve(reference_date, "0.0340")
    eur_6m = rate_index("EURIBOR", "6M", Currency.EUR)
    eur_3m = rate_index("EURIBOR", "3M", Currency.EUR)
    usd_3m = rate_index("SOFR", "3M", Currency.USD)
    multicurve_environment = (
        MultiCurveEnvironmentBuilder()
        .add_discount_curve(Currency.EUR, eur_discount_curve)
        .add_discount_curve(Currency.USD, usd_discount_curve)
        .add_projection_curve(eur_6m, eur_term_6m_curve)
        .add_projection_curve(eur_3m, eur_term_3m_curve)
        .add_projection_curve(usd_3m, usd_sofr_curve)
        .build()
    )
    return AnalyticsCurves(
        discount_curve=eur_discount_curve,
        forward_curve=eur_term_6m_curve,
        multicurve_environment=multicurve_environment,
        projection_curves={
            str(eur_6m): eur_term_6m_curve,
            str(eur_3m): eur_term_3m_curve,
            str(usd_3m): usd_sofr_curve,
        },
    )


def _asset_swap(settlement: Date) -> AssetSwap:
    return AssetSwap(
        bond=_bond(settlement),
        settlement_date=settlement,
        floating_leg=FloatingLegSpec(
            pay_receive=PayReceive.RECEIVE,
            notional=Decimal("100"),
            index_name="EURIBOR",
            index_tenor="6M",
            currency=Currency.EUR,
            schedule=ScheduleDefinition(frequency=Frequency.SEMI_ANNUAL),
        ),
        market_dirty_price=Decimal("100.00"),
    )


def _local_basis_swap(reference_date: Date) -> BasisSwap:
    return BasisSwap(
        effective_date=reference_date,
        maturity_date=reference_date.add_years(5),
        pay_leg=FloatingLegSpec(
            pay_receive=PayReceive.PAY,
            notional=Decimal("100"),
            index_name="EURIBOR",
            index_tenor="6M",
            currency=Currency.EUR,
            schedule=ScheduleDefinition(frequency=Frequency.SEMI_ANNUAL),
        ),
        receive_leg=FloatingLegSpec(
            pay_receive=PayReceive.RECEIVE,
            notional=Decimal("100"),
            index_name="EURIBOR",
            index_tenor="3M",
            currency=Currency.EUR,
            schedule=ScheduleDefinition(frequency=Frequency.QUARTERLY),
        ),
        quoted_leg=PayReceive.RECEIVE,
    )


def _cross_currency_basis_swap(reference_date: Date) -> CrossCurrencyBasisSwap:
    return CrossCurrencyBasisSwap(
        effective_date=reference_date,
        maturity_date=reference_date.add_years(5),
        pay_leg=FloatingLegSpec(
            pay_receive=PayReceive.PAY,
            notional=Decimal("100"),
            index_name="EURIBOR",
            index_tenor="3M",
            currency=Currency.EUR,
            schedule=ScheduleDefinition(frequency=Frequency.QUARTERLY),
        ),
        receive_leg=FloatingLegSpec(
            pay_receive=PayReceive.RECEIVE,
            notional=Decimal("110"),
            index_name="SOFR",
            index_tenor="3M",
            currency=Currency.USD,
            schedule=ScheduleDefinition(frequency=Frequency.QUARTERLY),
        ),
        spot_fx_rate=Decimal("1.10"),
        quoted_leg=PayReceive.RECEIVE,
    )


def test_bond_transforms_to_common_currency_floating_via_asset_swap_basis_and_ccbs() -> None:
    settlement = Date.from_ymd(2026, 1, 15)
    curves = _curves(settlement)
    asset_swap = _asset_swap(settlement)
    local_basis_swap = _local_basis_swap(settlement)
    cross_currency_basis_swap = _cross_currency_basis_swap(settlement)

    floating_view = bond_to_common_currency_floating(
        asset_swap,
        curves,
        local_basis_swap=local_basis_swap,
        cross_currency_basis_swap=cross_currency_basis_swap,
    )

    assert floating_view.asset_swap_spread == AssetSwapPricer().par_spread(asset_swap, curves)
    assert floating_view.same_currency_basis == BasisSwapPricer().par_spread(local_basis_swap, curves)
    assert floating_view.cross_currency_basis == CrossCurrencyBasisSwapPricer().par_spread(
        cross_currency_basis_swap,
        curves,
    )
    assert floating_view.common_currency_floating_spread == (
        floating_view.asset_swap_spread + floating_view.same_currency_basis + floating_view.cross_currency_basis
    )
    assert floating_view.target_currency is Currency.USD
    assert floating_view.target_index_name == "SOFR"


def test_bond_transforms_to_common_currency_fixed_rate_by_adding_swap_yardstick() -> None:
    settlement = Date.from_ymd(2026, 1, 15)
    curves = _curves(settlement)
    asset_swap = _asset_swap(settlement)
    local_basis_swap = _local_basis_swap(settlement)
    cross_currency_basis_swap = _cross_currency_basis_swap(settlement)

    fixed_view = bond_to_common_currency_fixed(
        asset_swap,
        curves,
        local_basis_swap=local_basis_swap,
        cross_currency_basis_swap=cross_currency_basis_swap,
    )

    assert fixed_view.target_currency is Currency.USD
    assert fixed_view.target_index_name == "SOFR"
    assert fixed_view.common_currency_fixed_rate == (
        fixed_view.par_swap_rate + fixed_view.floating_view.common_currency_floating_spread
    )
