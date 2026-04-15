from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pytest

from fuggers_py.core import Currency, Date
from fuggers_py.market.state import AnalyticsCurves
from fuggers_py.core import YearMonth
from fuggers_py.market.snapshot import InflationFixing
from fuggers_py.market.sources import InMemoryInflationFixingSource
from fuggers_py.reference.inflation import USD_CPI_U_NSA, reference_cpi
from fuggers_py.pricers.rates import InflationSwapPricer
from fuggers_py.products.rates import PayReceive, ZeroCouponInflationSwap

from tests.helpers._rates_helpers import flat_curve


def _fixing(month: str, value: str) -> InflationFixing:
    return InflationFixing(
        index_name="CPURNSA",
        observation_month=YearMonth.parse(month),
        value=Decimal(value),
    )


@dataclass(frozen=True, slots=True)
class FixingProjection:
    fixing_source: InMemoryInflationFixingSource

    def reference_cpi(self, date: Date, convention) -> Decimal:
        return reference_cpi(date, convention, self.fixing_source)


def _projection() -> FixingProjection:
    return FixingProjection(
        InMemoryInflationFixingSource(
            [
                _fixing("2023-10", "100"),
                _fixing("2023-11", "110"),
                _fixing("2024-10", "120"),
                _fixing("2024-11", "130"),
            ]
        )
    )


def _swap(*, pay_receive: PayReceive = PayReceive.PAY, fixed_rate: str | Decimal = "0.02") -> ZeroCouponInflationSwap:
    return ZeroCouponInflationSwap.new(
        trade_date=Date.from_ymd(2024, 1, 10),
        effective_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2025, 1, 15),
        notional=Decimal("1000000"),
        fixed_rate=Decimal(str(fixed_rate)),
        pay_receive=pay_receive,
        currency=Currency.USD,
        inflation_convention=USD_CPI_U_NSA,
        instrument_id="ZCIS-1",
    )


def test_zero_coupon_inflation_swap_par_rate_prices_to_zero() -> None:
    swap = _swap(fixed_rate="0.00")
    projection = _projection()
    discount_curve = flat_curve(Date.from_ymd(2024, 1, 10), "0.03")
    pricer = InflationSwapPricer()

    par_rate = pricer.par_fixed_rate(
        swap,
        discount_curve=discount_curve,
        inflation_projection=projection,
    )
    par_swap = _swap(fixed_rate=par_rate)

    assert float(
        pricer.pv(
            par_swap,
            discount_curve=discount_curve,
            inflation_projection=projection,
        )
    ) == pytest.approx(0.0, abs=1e-10)


def test_zero_coupon_inflation_swap_payer_receiver_sign_flip() -> None:
    projection = _projection()
    discount_curve = flat_curve(Date.from_ymd(2024, 1, 10), "0.03")
    pricer = InflationSwapPricer()
    payer = _swap(pay_receive=PayReceive.PAY, fixed_rate="0.015")
    receiver = _swap(pay_receive=PayReceive.RECEIVE, fixed_rate="0.015")

    payer_result = pricer.price(
        payer,
        discount_curve=discount_curve,
        inflation_projection=projection,
    )
    receiver_result = pricer.price(
        receiver,
        discount_curve=discount_curve,
        inflation_projection=projection,
    )

    assert payer_result.present_value == -receiver_result.present_value
    assert payer_result.fixed_leg_pv == -receiver_result.fixed_leg_pv
    assert payer_result.inflation_leg_pv == -receiver_result.inflation_leg_pv
    assert payer_result.pv01 == -receiver_result.pv01


def test_zero_coupon_inflation_swap_interpolation_affects_index_initial_and_final() -> None:
    swap = _swap(fixed_rate="0.015")
    projection = _projection()
    pricer = InflationSwapPricer()
    discount_curve = flat_curve(Date.from_ymd(2024, 1, 10), "0.03")

    result = pricer.price(
        swap,
        discount_curve=discount_curve,
        inflation_projection=projection,
    )

    expected_initial = Decimal("100") + (Decimal(14) / Decimal(31)) * Decimal("10")
    expected_final = Decimal("120") + (Decimal(14) / Decimal(31)) * Decimal("10")

    assert float(result.index_initial) == pytest.approx(float(expected_initial), abs=1e-12)
    assert float(result.index_final) == pytest.approx(float(expected_final), abs=1e-12)
    assert result.index_final > result.index_initial


def test_zero_coupon_inflation_swap_default_effective_date_is_t_plus_two_business_days() -> None:
    swap = ZeroCouponInflationSwap.new(
        trade_date=Date.from_ymd(2026, 1, 2),
        maturity_date=Date.from_ymd(2027, 1, 15),
        notional=Decimal("1000000"),
        fixed_rate=Decimal("0.02"),
        pay_receive=PayReceive.PAY,
        currency=Currency.USD,
        inflation_convention=USD_CPI_U_NSA,
    )

    assert swap.effective_date == Date.from_ymd(2026, 1, 6)


def test_zero_coupon_inflation_swap_pricer_uses_projection_curves() -> None:
    swap = _swap(fixed_rate="0.015")
    projection = _projection()
    discount_curve = flat_curve(Date.from_ymd(2024, 1, 10), "0.03")
    curves = AnalyticsCurves(
        discount_curve=discount_curve,
        projection_curves={"CPURNSA": projection},
    )

    result = InflationSwapPricer().price(swap, curves=curves)

    assert result.par_fixed_rate is not None
    assert result.present_value is not None
    assert result.fixed_leg_pv is not None
    assert result.inflation_leg_pv is not None
    assert result.pv01 is not None
