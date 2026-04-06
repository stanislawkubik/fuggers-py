from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from fuggers_py.core import Currency, Date, Frequency
from fuggers_py.calc import RatesPricingRouter, RoutedFraPricingResult
from fuggers_py.calc import BasisSwapQuoteOutput, SwapQuoteOutput
from fuggers_py.core import YearMonth
from fuggers_py.market.snapshot import InflationFixing
from fuggers_py.market.sources import InMemoryInflationFixingSource
from fuggers_py.reference.inflation import USD_CPI_U_NSA, reference_cpi
from fuggers_py.products.rates import (
    BasisSwap,
    FixedFloatSwap,
    FixedLegSpec,
    FloatingLegSpec,
    Fra,
    Ois,
    PayReceive,
    ScheduleDefinition,
    StandardCouponInflationSwap,
    ZeroCouponInflationSwap,
)

from tests.helpers._rates_helpers import flat_curve, multicurve_analytics_curves, rate_index


class _FixingProjection:
    def __init__(self) -> None:
        self.fixings = InMemoryInflationFixingSource(
            [
                InflationFixing("CPURNSA", YearMonth(2023, 10), Decimal("100")),
                InflationFixing("CPURNSA", YearMonth(2023, 11), Decimal("110")),
                InflationFixing("CPURNSA", YearMonth(2024, 4), Decimal("120")),
                InflationFixing("CPURNSA", YearMonth(2024, 5), Decimal("121")),
                InflationFixing("CPURNSA", YearMonth(2024, 10), Decimal("120")),
                InflationFixing("CPURNSA", YearMonth(2024, 11), Decimal("130")),
            ]
        )

    def reference_cpi(self, date: Date, convention) -> Decimal:
        return reference_cpi(date, convention, self.fixings)


def _swap(reference_date: Date, *, cls=FixedFloatSwap):
    return cls(
        effective_date=reference_date,
        maturity_date=reference_date.add_years(2),
        fixed_leg=FixedLegSpec(
            pay_receive=PayReceive.RECEIVE,
            notional=Decimal("1000000"),
            fixed_rate=Decimal("0.04"),
            currency=Currency.USD,
            schedule=ScheduleDefinition(frequency=Frequency.SEMI_ANNUAL),
        ),
        floating_leg=FloatingLegSpec(
            pay_receive=PayReceive.PAY,
            notional=Decimal("1000000"),
            index_name="SOFR",
            index_tenor="3M",
            currency=Currency.USD,
            schedule=ScheduleDefinition(frequency=Frequency.QUARTERLY),
        ),
    )


def test_rates_pricing_router_dispatches_swap_fra_and_basis_swap() -> None:
    reference_date = Date.from_ymd(2026, 1, 2)
    discount_curve = flat_curve(reference_date, "0.03")
    sofr_curve = flat_curve(reference_date, "0.035")
    term_curve = flat_curve(reference_date, "0.0375")
    curves = multicurve_analytics_curves(
        discount_curve=discount_curve,
        discount_currency=Currency.USD,
        forward_curve=sofr_curve,
        projection_curves={
            rate_index("SOFR", "3M"): sofr_curve,
            rate_index("TERM", "6M"): term_curve,
        },
    )
    router = RatesPricingRouter()
    swap = _swap(reference_date)
    fra = Fra(
        start_date=reference_date.add_months(6),
        end_date=reference_date.add_months(9),
        notional=Decimal("1000000"),
        fixed_rate=Decimal("0.034"),
        pay_receive=PayReceive.RECEIVE,
        currency=Currency.USD,
        index_name="SOFR",
        index_tenor="3M",
        instrument_id="FRA-1",
    )
    basis_swap = BasisSwap(
        effective_date=reference_date,
        maturity_date=reference_date.add_years(3),
        pay_leg=FloatingLegSpec(
            pay_receive=PayReceive.PAY,
            notional=Decimal("1000000"),
            index_name="SOFR",
            index_tenor="3M",
            currency=Currency.USD,
            schedule=ScheduleDefinition(frequency=Frequency.QUARTERLY),
        ),
        receive_leg=FloatingLegSpec(
            pay_receive=PayReceive.RECEIVE,
            notional=Decimal("1000000"),
            index_name="TERM",
            index_tenor="6M",
            currency=Currency.USD,
            schedule=ScheduleDefinition(frequency=Frequency.SEMI_ANNUAL),
        ),
        instrument_id="BASIS-1",
    )

    swap_result = router.price(swap, curves=curves)
    fra_result = router.price(fra, curves=curves)
    basis_result = router.price(basis_swap, curves=curves)

    assert isinstance(swap_result, SwapQuoteOutput)
    assert swap_result.pricing_path == "swap"
    assert swap_result.pv01 is not None
    assert isinstance(fra_result, RoutedFraPricingResult)
    assert fra_result.pricing_path == "fra"
    assert fra_result.instrument_id is not None
    assert fra_result.dv01 is not None
    assert fra_result.dv01 == fra_result.pv01
    assert isinstance(basis_result, BasisSwapQuoteOutput)
    assert basis_result.pricing_path == "basis_swap"
    assert basis_result.pv01 is not None


def test_rates_pricing_router_prices_ois_and_batch() -> None:
    reference_date = Date.from_ymd(2026, 1, 2)
    curve = flat_curve(reference_date, "0.03")
    curves = multicurve_analytics_curves(
        discount_curve=curve,
        discount_currency=Currency.USD,
        forward_curve=curve,
        projection_curves={rate_index("SOFR", "3M"): curve},
    )
    router = RatesPricingRouter()
    ois = _swap(reference_date, cls=Ois)
    fra = Fra(
        start_date=reference_date.add_months(6),
        end_date=reference_date.add_months(9),
        notional=Decimal("1000000"),
        fixed_rate=Decimal("0.03"),
        pay_receive=PayReceive.RECEIVE,
        currency=Currency.USD,
        index_name="SOFR",
        index_tenor="3M",
    )

    results = router.price_batch((ois, fra), curves=curves)

    assert isinstance(results[0], SwapQuoteOutput)
    assert results[0].pricing_path == "ois"
    assert isinstance(results[1], RoutedFraPricingResult)
    assert results[1].dv01 == results[1].pv01


def test_rates_pricing_router_dispatches_zero_coupon_inflation_swap() -> None:
    reference_date = Date.from_ymd(2024, 1, 10)
    curves = multicurve_analytics_curves(
        discount_curve=flat_curve(reference_date, "0.03"),
        discount_currency=Currency.USD,
    )
    curves.projection_curves["CPURNSA"] = _FixingProjection()
    router = RatesPricingRouter()
    swap = ZeroCouponInflationSwap.new(
        trade_date=reference_date,
        effective_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2025, 1, 15),
        notional=Decimal("1000000"),
        fixed_rate=Decimal("0.02"),
        pay_receive=PayReceive.PAY,
        currency=Currency.USD,
        inflation_convention=USD_CPI_U_NSA,
        instrument_id="ZCIS-1",
    )

    result = router.price(swap, curves=curves)

    assert isinstance(result, SwapQuoteOutput)
    assert result.pricing_path == "zero_coupon_inflation_swap"
    assert result.par_rate is not None
    assert result.pv01 is not None


def test_rates_pricing_router_dispatches_standard_coupon_inflation_swap() -> None:
    reference_date = Date.from_ymd(2024, 1, 10)
    curves = multicurve_analytics_curves(
        discount_curve=flat_curve(reference_date, "0.03"),
        discount_currency=Currency.USD,
    )
    curves = replace(curves, inflation_curve=_FixingProjection())
    router = RatesPricingRouter()
    swap = StandardCouponInflationSwap.new(
        trade_date=reference_date,
        effective_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2025, 1, 15),
        notional=Decimal("1000000"),
        fixed_rate=Decimal("0.02"),
        pay_receive=PayReceive.PAY,
        currency=Currency.USD,
        inflation_convention=USD_CPI_U_NSA,
        normalize_effective_date_to_reference_month_start=False,
        instrument_id="SCIS-1",
    )

    result = router.price(swap, curves=curves)

    assert isinstance(result, SwapQuoteOutput)
    assert result.pricing_path == "standard_coupon_inflation_swap"
    assert result.par_rate is not None
    assert result.pv01 is not None
