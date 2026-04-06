from __future__ import annotations

import importlib
from decimal import Decimal
from math import exp

import pytest

from fuggers_py.measures.spreads import (
    ASWType as AnalyticsASWType,
    BenchmarkKind,
    BenchmarkSpec,
    GovernmentCurve,
    ISpreadCalculator,
    SecurityId,
    Sovereign,
    g_spread,
    g_spread_bps,
    g_spread_with_benchmark,
    g_spread_with_benchmark_bps,
    i_spread,
    i_spread_bps,
    z_spread_from_curve,
)
from fuggers_py.measures.errors import AnalyticsError
from fuggers_py.reference.bonds.types import ASWType
from fuggers_py.products.bonds.traits import BondCashFlow, CashFlowType
from fuggers_py.reference.bonds.types import Tenor
from fuggers_py.market.curves import DiscountCurveBuilder
from fuggers_py.core import Currency, Date


def test_asw_type_remains_available_from_analytics_surface() -> None:
    assert AnalyticsASWType is ASWType
    assert not hasattr(importlib.import_module("fuggers_py.measures.spreads.asw"), "ASWType")


def test_security_id_wrapper() -> None:
    sec = SecurityId.cusip_unchecked("91282CJN6")
    assert sec.id_type() == "CUSIP"
    assert sec.as_str() == "91282CJN6"


def test_benchmark_spec_helpers() -> None:
    assert BenchmarkSpec.interpolated().kind.name == "INTERPOLATED"
    assert BenchmarkSpec.ten_year().tenor == Tenor.parse("10Y")
    assert BenchmarkSpec.five_year().tenor == Tenor.parse("5Y")
    assert BenchmarkSpec.nearest().kind.name == "NEAREST"
    explicit = BenchmarkSpec.explicit(Decimal("0.0425"))
    assert explicit.explicit_yield == Decimal("0.0425")
    assert "Explicit" in explicit.description()


def test_sovereign_properties() -> None:
    assert Sovereign.us_treasury().currency() == Currency.USD
    assert Sovereign.uk_gilt().currency() == Currency.GBP
    assert Sovereign.german_bund().currency() == Currency.EUR
    assert Sovereign.us_treasury().bond_name() == "Treasury"


def test_government_curve_interpolation() -> None:
    ref = Date.from_ymd(2020, 1, 1)
    curve = GovernmentCurve.us_treasury(ref)
    curve.add_benchmark(Tenor.parse("2Y"), Decimal("0.02"))
    curve.add_benchmark(Tenor.parse("5Y"), Decimal("0.03"))
    curve.add_benchmark(Tenor.parse("10Y"), Decimal("0.04"))

    mid = curve.interpolated_yield(7.0)
    assert Decimal("0.03") < mid < Decimal("0.04")


def test_g_spread_with_benchmark_date_respects_nearest_spec() -> None:
    ref = Date.from_ymd(2020, 1, 1)
    curve = GovernmentCurve.us_treasury(ref)
    curve.add_benchmark(Tenor.parse("2Y"), Decimal("0.02"))
    curve.add_benchmark(Tenor.parse("5Y"), Decimal("0.03"))
    curve.add_benchmark(Tenor.parse("10Y"), Decimal("0.04"))

    maturity = ref.add_years(7)
    spread = g_spread_with_benchmark(
        Decimal("0.05"),
        curve,
        maturity,
        benchmark=BenchmarkSpec.nearest(),
    )
    assert spread == Decimal("0.02")


def test_g_spread_with_benchmark_date_respects_ten_year_spec() -> None:
    ref = Date.from_ymd(2020, 1, 1)
    curve = GovernmentCurve.us_treasury(ref)
    curve.add_benchmark(Tenor.parse("2Y"), Decimal("0.02"))
    curve.add_benchmark(Tenor.parse("5Y"), Decimal("0.03"))
    curve.add_benchmark(Tenor.parse("10Y"), Decimal("0.04"))

    maturity = ref.add_years(7)
    spread = g_spread_with_benchmark(
        Decimal("0.05"),
        curve,
        maturity,
        benchmark=BenchmarkSpec.ten_year(),
    )
    assert spread == Decimal("0.01")


def test_government_curve_yield_for_date_honors_spec() -> None:
    ref = Date.from_ymd(2020, 1, 1)
    curve = GovernmentCurve.us_treasury(ref)
    curve.add_benchmark(Tenor.parse("2Y"), Decimal("0.02"))
    curve.add_benchmark(Tenor.parse("5Y"), Decimal("0.03"))
    curve.add_benchmark(Tenor.parse("10Y"), Decimal("0.04"))

    maturity = ref.add_years(7)
    assert curve.yield_for_date(maturity, spec=BenchmarkSpec.nearest()) == Decimal("0.03")
    assert curve.yield_for_date(maturity, spec=BenchmarkSpec.ten_year()) == Decimal("0.04")
    assert curve.yield_for_date(maturity, spec=BenchmarkSpec.explicit(Decimal("0.0425"))) == Decimal("0.0425")


def test_nearest_benchmark_tie_breaks_to_shorter_tenor() -> None:
    ref = Date.from_ymd(2020, 1, 1)
    curve = GovernmentCurve.us_treasury(ref)
    curve.add_benchmark(Tenor.parse("5Y"), Decimal("0.03"))
    curve.add_benchmark(Tenor.parse("10Y"), Decimal("0.04"))

    nearest = curve.nearest_benchmark(7.5)
    assert nearest.tenor == Tenor.parse("5Y")


def test_government_curve_boundary_and_error_paths() -> None:
    ref = Date.from_ymd(2020, 1, 1)
    empty = GovernmentCurve.us_treasury(ref)

    with pytest.raises(ValueError, match="No benchmarks available"):
        empty.nearest_benchmark(5.0)

    curve = GovernmentCurve.us_treasury(ref)
    curve.add_benchmark(Tenor.parse("2Y"), Decimal("0.02"))
    curve.add_benchmark(Tenor.parse("5Y"), Decimal("0.03"))

    assert curve.interpolated_yield(1.0) == Decimal("0.02")
    assert curve.interpolated_yield(7.0) == Decimal("0.03")
    assert curve.yield_for_tenor(Tenor.parse("3Y"), spec=BenchmarkSpec.explicit(Decimal("0.0275"))) == Decimal("0.0275")

    with pytest.raises(ValueError, match="tenor missing"):
        curve.yield_for_tenor(Tenor.parse("3Y"), spec=BenchmarkSpec(kind=BenchmarkKind.TENOR))


def test_g_spread_deterministic() -> None:
    result = g_spread(Decimal("0.05"), Decimal("0.0425"))
    assert float(result) == pytest.approx(0.0075, abs=1e-12)
    assert g_spread_bps(Decimal("0.05"), Decimal("0.0425")) == Decimal("75")


def test_i_spread_deterministic() -> None:
    result = i_spread(Decimal("0.055"), Decimal("0.04"))
    assert float(result) == pytest.approx(0.015, abs=1e-12)
    assert i_spread_bps(Decimal("0.055"), Decimal("0.04")) == Decimal("150")


def test_g_spread_benchmark_bps_wrapper_matches_decimal_result() -> None:
    ref = Date.from_ymd(2020, 1, 1)
    curve = GovernmentCurve.us_treasury(ref)
    curve.add_benchmark(Tenor.parse("5Y"), Decimal("0.03"))

    maturity = ref.add_years(5)
    assert g_spread_with_benchmark_bps(Decimal("0.05"), curve, maturity) == Decimal("200")


def test_ispread_rejects_settlement_after_maturity(fixed_rate_2025_bond) -> None:
    bond = fixed_rate_2025_bond
    ref = Date.from_ymd(2020, 1, 1)
    curve = DiscountCurveBuilder(reference_date=ref)
    curve.add_zero_rate(1.0, Decimal("0.02")).add_zero_rate(10.0, Decimal("0.02"))
    rate_curve = curve.build()

    calc = ISpreadCalculator(curve=rate_curve)
    assert calc.spread_decimal(bond, Decimal("0.05")) == Decimal("0.03")
    assert calc.spread_bps(bond, Decimal("0.05")) == Decimal("300")
    settlement = bond.maturity_date().add_days(1)
    with pytest.raises(AnalyticsError):
        calc.spread_bps(bond, Decimal("0.05"), settlement_date=settlement)


def test_z_spread_roundtrip() -> None:
    ref = Date.from_ymd(2020, 1, 1)
    curve = DiscountCurveBuilder(reference_date=ref)
    curve.add_zero_rate(1.0, Decimal("0.02")).add_zero_rate(3.0, Decimal("0.02"))
    rate_curve = curve.build()

    cashflows = [
        BondCashFlow(date=ref.add_years(1), amount=Decimal("5"), flow_type=CashFlowType.COUPON),
        BondCashFlow(date=ref.add_years(2), amount=Decimal("105"), flow_type=CashFlowType.COUPON_AND_PRINCIPAL),
    ]

    z = 0.015
    df_settle = float(rate_curve.discount_factor(ref))
    dirty_price = 0.0
    for cf in cashflows:
        t = float(ref.days_between(cf.date)) / 365.0
        df = float(rate_curve.discount_factor(cf.date)) / df_settle
        dirty_price += float(cf.factored_amount()) * df * exp(-z * t)

    recovered = z_spread_from_curve(
        cashflows,
        dirty_price=dirty_price,
        curve=rate_curve,
        settlement_date=ref,
    )
    assert float(recovered) == pytest.approx(z, abs=1e-4)
