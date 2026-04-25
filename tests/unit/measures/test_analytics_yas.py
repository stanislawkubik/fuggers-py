from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.bonds.analytics_pricing import BondPricer
from fuggers_py.bonds.spreads import BenchmarkSpec, GovernmentCurve, g_spread_with_benchmark_bps
from fuggers_py.bonds.yas import BloombergReference, SettlementInvoiceBuilder, YASCalculator
from fuggers_py.bonds.yields import current_yield_from_amount_pct
from fuggers_py.bonds.instruments import FixedBondBuilder
from fuggers_py._core import Tenor, YieldCalculationRules
from fuggers_py._core import Currency, Date, Frequency, Price
from tests.helpers._rates_helpers import flat_curve


def test_bloomberg_reference_boeing() -> None:
    ref = BloombergReference.boeing_2025()
    assert float(ref.ytm) == pytest.approx(4.905895, abs=1e-9)
    assert float(ref.g_spread_bps) == pytest.approx(448.5, abs=1e-9)
    assert float(ref.z_spread_bps) == pytest.approx(444.7, abs=1e-9)
    assert float(ref.modified_duration) == pytest.approx(4.209, abs=1e-9)
    assert float(ref.convexity) == pytest.approx(0.219, abs=1e-9)


def test_settlement_invoice_builder() -> None:
    builder = SettlementInvoiceBuilder(
        settlement_date=Date.from_ymd(2020, 6, 15),
        clean_price=Decimal("100"),
        accrued_interest=Decimal("1.25"),
        face_value=Decimal("100"),
        accrued_days=10,
    )
    invoice = builder.build()
    assert float(invoice.dirty_price) == pytest.approx(101.25, abs=1e-9)
    assert float(invoice.settlement_amount) == pytest.approx(
        float(invoice.principal_amount + invoice.accrued_amount),
        abs=1e-9,
    )


def test_yas_structural_consistency(fixed_rate_2025_bond) -> None:
    bond = fixed_rate_2025_bond
    settlement = Date.from_ymd(2020, 6, 15)

    curve = flat_curve(settlement, "0.03")

    calc = YASCalculator(curve=curve)
    analysis = calc.calculate(bond, Price.new(Decimal("105"), bond.currency()), settlement)

    assert analysis.invoice is not None
    assert analysis.modified_duration() == analysis.risk.modified_duration
    assert analysis.convexity() == analysis.risk.convexity
    assert analysis.dv01() == analysis.risk.dv01

    coupon_amount = bond.coupon_rate() * Decimal(100)
    assert analysis.current_yield == current_yield_from_amount_pct(coupon_amount, Decimal("105"))


def test_validate_bloomberg_smoke(fixed_rate_2025_bond) -> None:
    bond = fixed_rate_2025_bond
    settlement = Date.from_ymd(2020, 6, 15)
    curve = flat_curve(settlement, "0.03")

    calc = YASCalculator(curve=curve)
    failures = calc.validate_bloomberg(
        bond,
        Price.new(Decimal("105"), bond.currency()),
        settlement,
    )
    assert isinstance(failures, list)


def test_yas_calculator_populates_benchmark_fields_with_government_curve() -> None:
    issue = Date.from_ymd(2020, 1, 1)
    maturity = Date.from_ymd(2027, 1, 1)
    bond = (
        FixedBondBuilder.new()
        .with_issue_date(issue)
        .with_maturity_date(maturity)
        .with_coupon_rate(Decimal("0.05"))
        .with_frequency(Frequency.SEMI_ANNUAL)
        .with_currency(Currency.USD)
        .with_rules(YieldCalculationRules.us_corporate())
        .build()
    )

    settlement = Date.from_ymd(2020, 1, 1)
    curve = flat_curve(settlement, "0.03")

    gov_curve = GovernmentCurve.us_treasury(settlement)
    gov_curve.add_benchmark(Tenor.parse("2Y"), Decimal("0.02"))
    gov_curve.add_benchmark(Tenor.parse("5Y"), Decimal("0.03"))
    gov_curve.add_benchmark(Tenor.parse("10Y"), Decimal("0.04"))

    calc = YASCalculator(curve=curve, government_curve=gov_curve, benchmark=BenchmarkSpec.nearest())
    analysis = calc.calculate(bond, Price.new(Decimal("105"), bond.currency()), settlement)
    ytm = BondPricer().yield_to_maturity(bond, Price.new(Decimal("105"), bond.currency()), settlement).value()

    assert analysis.g_spread_bps is not None
    assert analysis.benchmark_spread_bps is not None
    assert analysis.benchmark_tenor is not None
    assert analysis.g_spread_bps == g_spread_with_benchmark_bps(
        ytm,
        gov_curve,
        bond.maturity_date(),
        benchmark=BenchmarkSpec.interpolated(),
    )
    assert analysis.benchmark_spread_bps != analysis.g_spread_bps


def test_yas_calculator_does_not_swallow_unexpected_zspread_errors(fixed_rate_2025_bond, monkeypatch) -> None:
    bond = fixed_rate_2025_bond
    settlement = Date.from_ymd(2020, 6, 15)
    curve = flat_curve(settlement, "0.03")

    calc = YASCalculator(curve=curve)

    import fuggers_py.bonds._yas.calculator as yas_calc_mod

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(yas_calc_mod, "z_spread", boom)

    with pytest.raises(RuntimeError, match="boom"):
        calc.calculate(bond, Price.new(Decimal("105"), bond.currency()), settlement)
