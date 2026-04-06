from __future__ import annotations

from decimal import Decimal

from fuggers_py.measures.rv import global_fixed_cashflow_rv, global_usd_sofr_rv
from fuggers_py.products.bonds import FixedBondBuilder
from fuggers_py.reference import YieldCalculationRules
from fuggers_py.core import Currency, Date, Frequency
from fuggers_py.market.curves import MultiCurveEnvironmentBuilder
from fuggers_py.calc import AnalyticsCurves
from fuggers_py.products.rates import (
    AssetSwap,
    BasisSwap,
    CrossCurrencyBasisSwap,
    FloatingLegSpec,
    PayReceive,
    ScheduleDefinition,
)

from tests.helpers._fitted_bond_helpers import exponential_model, fit_result
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


def _expected_classification(residual_bps: Decimal) -> str:
    if residual_bps > Decimal(0):
        return "CHEAP"
    if residual_bps < Decimal(0):
        return "RICH"
    return "NEUTRAL"


def test_global_fixed_cashflow_rv_compares_common_currency_fixed_rate_to_fitted_curve() -> None:
    settlement = Date.from_ymd(2026, 1, 15)
    result = global_fixed_cashflow_rv(
        _asset_swap(settlement),
        _curves(settlement),
        fit_result(curve_model=exponential_model(), regression_coefficient=Decimal("0.25")),
        local_basis_swap=_local_basis_swap(settlement),
        cross_currency_basis_swap=_cross_currency_basis_swap(settlement),
        threshold_bps=Decimal(0),
    )

    assert result.fixed_view.target_currency is Currency.USD
    assert result.residual_bps == result.residual * Decimal("10000")
    assert result.classification == _expected_classification(result.residual_bps)


def test_global_usd_sofr_rv_reports_yardstick_residual_in_bps() -> None:
    settlement = Date.from_ymd(2026, 1, 15)
    result = global_usd_sofr_rv(
        _asset_swap(settlement),
        _curves(settlement),
        yardstick_spread=Decimal("0.0150"),
        adjusted_cds_spread=Decimal("0.0125"),
        local_basis_swap=_local_basis_swap(settlement),
        cross_currency_basis_swap=_cross_currency_basis_swap(settlement),
        threshold_bps=Decimal(0),
    )

    assert result.floating_view.target_currency is Currency.USD
    assert result.floating_view.target_index_name == "SOFR"
    assert result.usd_sofr_measure.adjusted_cds_spread == Decimal("0.0125")
    assert result.residual_bps == result.usd_sofr_measure.residual_to_yardstick * Decimal("10000")
    assert result.classification == _expected_classification(result.residual_bps)
