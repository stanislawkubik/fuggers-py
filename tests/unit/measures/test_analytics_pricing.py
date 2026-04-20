from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._measures.pricing import BondPricer
from fuggers_py._pricers.bonds import BondPricer as BondsBondPricer
from fuggers_py._curves_impl import DiscountCurveBuilder
from fuggers_py._core import Date, Price


def test_price_result_dirty_equals_clean_plus_accrued(fixed_rate_2025_bond) -> None:
    bond = fixed_rate_2025_bond
    pricer = BondPricer()
    settlement = Date.from_ymd(2020, 6, 15)
    ytm = pricer._delegate.yield_from_price(
        bond,
        Price.new(Decimal("105"), bond.currency()),
        settlement,
    ).ytm
    result = pricer.price_from_yield(bond, ytm, settlement)
    assert float(result.dirty.as_percentage()) == pytest.approx(
        float(result.clean.as_percentage() + result.accrued),
        abs=1e-9,
    )


def test_curve_pricing_matches_manual_pv(fixed_rate_2025_bond) -> None:
    bond = fixed_rate_2025_bond
    settlement = Date.from_ymd(2020, 6, 15)

    builder = DiscountCurveBuilder(reference_date=settlement)
    builder.add_zero_rate(1.0, Decimal("0.03")).add_zero_rate(10.0, Decimal("0.03"))
    curve = builder.build()

    pricer = BondPricer()
    result = pricer.price_from_curve(bond, curve, settlement)

    df_settle = curve.discount_factor(settlement)
    manual = Decimal(0)
    for cf in bond.cash_flows():
        if cf.date <= settlement:
            continue
        df = curve.discount_factor(cf.date) / df_settle
        manual += cf.factored_amount() * df

    assert float(result.dirty.as_percentage()) == pytest.approx(float(manual), abs=1e-6)


def test_yield_roundtrip(fixed_rate_2025_bond) -> None:
    bond = fixed_rate_2025_bond
    pricer = BondPricer()
    settlement = Date.from_ymd(2020, 6, 15)
    price = Price.new(Decimal("105"), bond.currency())
    ytm = pricer.yield_to_maturity(bond, price, settlement)
    result = pricer.price_from_yield(bond, ytm, settlement)
    assert float(result.clean.as_percentage()) == pytest.approx(105.0, abs=1e-3)


def test_analytics_bonds_pricer_compatibility(fixed_rate_2025_bond) -> None:
    bond = fixed_rate_2025_bond
    settlement = Date.from_ymd(2020, 6, 15)
    ytm = BondsBondPricer().yield_from_price(
        bond,
        Price.new(Decimal("105"), bond.currency()),
        settlement,
    ).ytm

    analytics_price = BondPricer().price_from_yield(bond, ytm, settlement)
    bonds_price = BondsBondPricer().price_from_yield(bond, ytm, settlement)

    assert float(analytics_price.clean.as_percentage()) == pytest.approx(
        float(bonds_price.clean.as_percentage()),
        abs=1e-9,
    )


def test_price_result_fields(fixed_rate_2025_bond) -> None:
    bond = fixed_rate_2025_bond
    pricer = BondPricer()
    settlement = Date.from_ymd(2020, 6, 15)
    ytm = pricer._delegate.yield_from_price(
        bond,
        Price.new(Decimal("105"), bond.currency()),
        settlement,
    ).ytm
    result = pricer.price_from_yield(bond, ytm, settlement)
    assert result.clean is not None
    assert result.dirty is not None
    assert result.accrued is not None
    assert result.present_value is not None
