from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

import pytest

from fuggers_py._core import CalendarId, PayReceive
from fuggers_py._core import Currency, Date, Frequency
from fuggers_py._core.calendars import BusinessDayConvention
from fuggers_py._runtime.state import AnalyticsCurves
from fuggers_py.inflation import USD_CPI_U_NSA
from fuggers_py.inflation import InflationSwapPricer, StandardCouponInflationSwapPricingResult
from fuggers_py.inflation import StandardCouponInflationSwap
from fuggers_py.rates import ScheduleDefinition

from tests.helpers._rates_helpers import flat_curve


@dataclass(frozen=True, slots=True)
class ProjectionCurve:
    values: dict[Date, Decimal]

    def reference_cpi(self, date: Date, convention) -> Decimal:
        del convention
        return self.values[date]


def _inflation_curve() -> ProjectionCurve:
    return ProjectionCurve(
        values={
            Date.from_ymd(2024, 1, 2): Decimal("100.0"),
            Date.from_ymd(2024, 7, 2): Decimal("101.0"),
            Date.from_ymd(2025, 1, 2): Decimal("102.5"),
        }
    )


def _schedule() -> ScheduleDefinition:
    return ScheduleDefinition(
        frequency=Frequency.SEMI_ANNUAL,
        calendar=CalendarId.sifma(),
        business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING,
    )


def _swap(*, pay_receive: PayReceive = PayReceive.PAY, fixed_rate: str | Decimal = "0.02") -> StandardCouponInflationSwap:
    return StandardCouponInflationSwap.new(
        trade_date=Date.from_ymd(2024, 1, 10),
        effective_date=Date.from_ymd(2024, 1, 2),
        maturity_date=Date.from_ymd(2025, 1, 2),
        notional=Decimal("1000000"),
        fixed_rate=Decimal(str(fixed_rate)),
        pay_receive=pay_receive,
        currency=Currency.USD,
        inflation_convention=USD_CPI_U_NSA,
        schedule=_schedule(),
        normalize_effective_date_to_reference_month_start=False,
        instrument_id="SCIS-1",
    )


def test_standard_coupon_inflation_swap_generates_schedule_and_allows_explicit_periods() -> None:
    generated = _swap()
    generated_periods = generated.fixed_periods()

    explicit = StandardCouponInflationSwap.new(
        trade_date=Date.from_ymd(2024, 1, 10),
        effective_date=Date.from_ymd(2024, 1, 2),
        maturity_date=Date.from_ymd(2025, 1, 2),
        notional=Decimal("1000000"),
        fixed_rate=Decimal("0.02"),
        pay_receive=PayReceive.PAY,
        currency=Currency.USD,
        inflation_convention=USD_CPI_U_NSA,
        schedule=_schedule(),
        normalize_effective_date_to_reference_month_start=False,
        fixed_periods=generated_periods,
        inflation_periods=generated_periods,
    )

    assert len(generated_periods) == 2
    assert generated_periods[0].start_date == Date.from_ymd(2024, 1, 2)
    assert generated_periods[-1].end_date == Date.from_ymd(2025, 1, 2)
    assert explicit.fixed_periods() == generated_periods
    assert explicit.inflation_periods() == generated_periods


def test_standard_coupon_inflation_swap_normalizes_effective_date_to_reference_month_start() -> None:
    swap = StandardCouponInflationSwap.new(
        trade_date=Date.from_ymd(2024, 1, 10),
        maturity_date=Date.from_ymd(2025, 1, 2),
        notional=Decimal("1000000"),
        fixed_rate=Decimal("0.02"),
        pay_receive=PayReceive.PAY,
        currency=Currency.USD,
        inflation_convention=USD_CPI_U_NSA,
        schedule=_schedule(),
    )

    assert swap.effective_date == Date.from_ymd(2024, 1, 2)


def test_standard_coupon_inflation_swap_par_rate_prices_to_zero() -> None:
    swap = _swap(fixed_rate="0.00")
    discount_curve = flat_curve(Date.from_ymd(2024, 1, 10), "0.03")
    pricer = InflationSwapPricer()
    curve = _inflation_curve()

    par_rate = pricer.par_fixed_rate(
        swap,
        discount_curve=discount_curve,
        inflation_projection=curve,
    )
    par_swap = replace(swap, fixed_rate=par_rate)

    assert float(
        pricer.pv(
            par_swap,
            discount_curve=discount_curve,
            inflation_projection=curve,
        )
    ) == pytest.approx(0.0, abs=1e-10)


def test_standard_coupon_inflation_swap_price_returns_period_breakdown() -> None:
    swap = _swap(fixed_rate="0.02")
    discount_curve = flat_curve(Date.from_ymd(2024, 1, 10), "0.03")
    curve = _inflation_curve()

    result = InflationSwapPricer().price(
        swap,
        discount_curve=discount_curve,
        inflation_projection=curve,
    )

    assert isinstance(result, StandardCouponInflationSwapPricingResult)
    assert len(result.periods) == 2
    assert result.periods[0].index_initial == Decimal("100.0")
    assert result.periods[0].index_final == Decimal("101.0")
    assert float(result.periods[0].inflation_rate) == pytest.approx(0.01, abs=1e-12)
    assert result.fixed_leg_pv < Decimal(0)
    assert result.inflation_leg_pv > Decimal(0)
    assert result.pv01 < Decimal(0)


def test_standard_coupon_inflation_swap_payer_receiver_sign_flip() -> None:
    discount_curve = flat_curve(Date.from_ymd(2024, 1, 10), "0.03")
    curve = _inflation_curve()
    pricer = InflationSwapPricer()

    payer = pricer.price(
        _swap(pay_receive=PayReceive.PAY, fixed_rate="0.02"),
        discount_curve=discount_curve,
        inflation_projection=curve,
    )
    receiver = pricer.price(
        _swap(pay_receive=PayReceive.RECEIVE, fixed_rate="0.02"),
        discount_curve=discount_curve,
        inflation_projection=curve,
    )

    assert payer.present_value == -receiver.present_value
    assert payer.fixed_leg_pv == -receiver.fixed_leg_pv
    assert payer.inflation_leg_pv == -receiver.inflation_leg_pv


def test_standard_coupon_inflation_swap_uses_analytics_curves_inflation_curve() -> None:
    swap = _swap(fixed_rate="0.02")
    curves = AnalyticsCurves(
        discount_curve=flat_curve(Date.from_ymd(2024, 1, 10), "0.03"),
        inflation_curve=_inflation_curve(),
    )

    result = InflationSwapPricer().price(swap, curves=curves)

    assert isinstance(result, StandardCouponInflationSwapPricingResult)
    assert result.par_fixed_rate > Decimal(0)


def test_standard_coupon_inflation_swap_requires_inflation_projection() -> None:
    with pytest.raises(ValueError, match="inflation projection"):
        InflationSwapPricer().pv(
            _swap(),
            discount_curve=flat_curve(Date.from_ymd(2024, 1, 10), "0.03"),
        )
