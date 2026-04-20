from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._core import Currency, Date, PayReceive
from fuggers_py._core.daycounts import DayCountConvention
from fuggers_py._market.state import AnalyticsCurves
from fuggers_py._core import YearMonth
from fuggers_py._market.snapshot import InflationFixing
from fuggers_py._market.sources import InMemoryInflationFixingSource
from fuggers_py._curves_impl.inflation import bootstrap_inflation_curve
from fuggers_py.inflation import MissingInflationFixing, USD_CPI_U_NSA, reference_cpi
from fuggers_py.inflation import InflationSwapPricer
from fuggers_py.inflation import ZeroCouponInflationSwap
from tests.helpers._rates_helpers import flat_curve


def _fixing(month: str, value: str) -> InflationFixing:
    return InflationFixing(
        index_name="CPURNSA",
        observation_month=YearMonth.parse(month),
        value=Decimal(value),
    )


def _fixing_source() -> InMemoryInflationFixingSource:
    return InMemoryInflationFixingSource(
        [
            _fixing("2023-10", "100"),
            _fixing("2023-11", "110"),
        ]
    )


def _discount_curve():
    return flat_curve(Date.from_ymd(2024, 1, 10), "0.03")


def _swap(*, maturity_date: Date, fixed_rate: str, instrument_id: str) -> ZeroCouponInflationSwap:
    return ZeroCouponInflationSwap.new(
        trade_date=Date.from_ymd(2024, 1, 10),
        effective_date=Date.from_ymd(2024, 1, 15),
        maturity_date=maturity_date,
        notional=Decimal("1000000"),
        fixed_rate=Decimal(fixed_rate),
        pay_receive=PayReceive.PAY,
        currency=Currency.USD,
        inflation_convention=USD_CPI_U_NSA,
        instrument_id=instrument_id,
    )


def _bootstrap_result():
    return bootstrap_inflation_curve(
        [
            _swap(maturity_date=Date.from_ymd(2025, 1, 15), fixed_rate="0.0200", instrument_id="ZCIS-1Y"),
            _swap(maturity_date=Date.from_ymd(2026, 1, 15), fixed_rate="0.0350", instrument_id="ZCIS-2Y"),
        ],
        fixing_source=_fixing_source(),
        discount_curve=_discount_curve(),
    )


def test_bootstrap_reprices_input_zero_coupon_inflation_swaps() -> None:
    result = _bootstrap_result()
    pricer = InflationSwapPricer()

    for point, swap in zip(
        result.points,
        [
            _swap(maturity_date=Date.from_ymd(2025, 1, 15), fixed_rate="0.0200", instrument_id="ZCIS-1Y"),
            _swap(maturity_date=Date.from_ymd(2026, 1, 15), fixed_rate="0.0350", instrument_id="ZCIS-2Y"),
        ],
        strict=True,
    ):
        price = pricer.price(
            swap,
            discount_curve=_discount_curve(),
            inflation_projection=result.curve,
        )
        assert float(point.fitted_fixed_rate) == pytest.approx(float(point.market_fixed_rate), abs=1e-12)
        assert float(point.residual_pv) == pytest.approx(0.0, abs=1e-8)
        assert float(price.present_value) == pytest.approx(0.0, abs=1e-8)


def test_bootstrapped_curve_projects_reference_cpi_and_index_ratios() -> None:
    result = _bootstrap_result()
    reference_date = Date.from_ymd(2024, 1, 15)
    one_year_date = Date.from_ymd(2025, 1, 15)
    two_year_date = Date.from_ymd(2026, 1, 15)
    anchor_reference_cpi = reference_cpi(reference_date, USD_CPI_U_NSA, _fixing_source())

    assert result.anchor_reference_cpi == anchor_reference_cpi
    assert float(result.curve.projected_reference_cpi(one_year_date)) == pytest.approx(
        float(anchor_reference_cpi * Decimal("1.02")),
        abs=1e-12,
    )
    assert result.curve.projected_index_ratio(one_year_date, reference_date) == Decimal("1.02")
    assert result.curve.projected_index_ratio(two_year_date, reference_date) == Decimal("1.035")
    assert float(result.curve.projected_index_ratio(two_year_date, one_year_date)) == pytest.approx(
        float(Decimal("1.035") / Decimal("1.02")),
        abs=1e-12,
    )


def test_bootstrapped_curve_interpolates_consistently_between_pillars() -> None:
    result = _bootstrap_result()
    mid_date = Date.from_ymd(2025, 7, 15)
    one_year_date = Date.from_ymd(2025, 1, 15)
    two_year_date = Date.from_ymd(2026, 1, 15)
    day_count = DayCountConvention.ACT_365_FIXED.to_day_count()
    tau_one = day_count.year_fraction(result.curve.reference_date, one_year_date)
    tau_mid = day_count.year_fraction(result.curve.reference_date, mid_date)
    tau_two = day_count.year_fraction(result.curve.reference_date, two_year_date)
    weight = (tau_mid - tau_one) / (tau_two - tau_one)
    expected_ratio = Decimal("1.02") + weight * (Decimal("1.035") - Decimal("1.02"))

    ratio = result.curve.projected_index_ratio(mid_date, result.curve.reference_date)

    assert float(ratio) == pytest.approx(float(expected_ratio), abs=1e-12)
    assert Decimal("1.02") < ratio < Decimal("1.035")


def test_bootstrap_requires_anchor_fixings() -> None:
    with pytest.raises(MissingInflationFixing):
        bootstrap_inflation_curve(
            [_swap(maturity_date=Date.from_ymd(2025, 1, 15), fixed_rate="0.0200", instrument_id="ZCIS-1Y")],
            fixing_source=InMemoryInflationFixingSource([]),
            discount_curve=_discount_curve(),
        )


def test_bootstrap_requires_increasing_maturity_order() -> None:
    with pytest.raises(ValueError, match="strictly increasing maturity ordering"):
        bootstrap_inflation_curve(
            [
                _swap(maturity_date=Date.from_ymd(2026, 1, 15), fixed_rate="0.0350", instrument_id="ZCIS-2Y"),
                _swap(maturity_date=Date.from_ymd(2025, 1, 15), fixed_rate="0.0200", instrument_id="ZCIS-1Y"),
            ],
            fixing_source=_fixing_source(),
            discount_curve=_discount_curve(),
        )


def test_analytics_curves_resolve_bootstrapped_inflation_curve() -> None:
    result = _bootstrap_result()
    curves = AnalyticsCurves(
        discount_curve=_discount_curve(),
        inflation_curves={"CPURNSA": result.curve},
    )
    swap = _swap(maturity_date=Date.from_ymd(2025, 7, 15), fixed_rate="0.0275", instrument_id="ZCIS-18M")

    assert curves.get("inflation:cpurnsa") is result.curve

    priced = InflationSwapPricer().price(swap, curves=curves)

    assert priced.par_fixed_rate is not None
    assert priced.present_value is not None
