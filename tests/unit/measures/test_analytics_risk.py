from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.bonds.analytics_pricing import BondPricer
from fuggers_py.bonds.risk import (
    BondRiskCalculator,
    analytical_convexity,
    dv01_from_duration,
    dv01_per_100_face,
    effective_duration,
    macaulay_duration,
    modified_duration,
    notional_from_dv01,
    price_change_with_convexity,
)
from fuggers_py._core import Date, Price


def test_dv01_formula_example() -> None:
    dv01 = dv01_from_duration(Decimal("5.0"), Decimal("105.0"), Decimal("1000000"))
    assert float(dv01) == pytest.approx(525.0, abs=1e-9)


def test_dv01_per_100_face() -> None:
    dv01 = dv01_per_100_face(Decimal("5.0"), Decimal("100.0"))
    assert float(dv01) == pytest.approx(0.05, abs=1e-9)


def test_notional_from_dv01() -> None:
    notional = notional_from_dv01(Decimal("1000"), Decimal("5.0"), Decimal("100.0"))
    assert float(notional) == pytest.approx(2_000_000, abs=1e-6)


def test_price_change_with_convexity() -> None:
    change = price_change_with_convexity(Decimal("5.0"), Decimal("50.0"), Decimal("100.0"), Decimal("0.01"))
    assert float(change) == pytest.approx(-4.75, abs=1e-6)


def test_bond_risk_sanity(fixed_rate_2025_bond) -> None:
    bond = fixed_rate_2025_bond
    settlement = Date.from_ymd(2020, 6, 15)
    price = Price.new(Decimal("100"), bond.currency())
    ytm = BondPricer().yield_to_maturity(bond, price, settlement)

    metrics = BondRiskCalculator(bond=bond, ytm=ytm, settlement_date=settlement).all_metrics()
    assert metrics.macaulay_duration > metrics.modified_duration > 0
    assert metrics.convexity > 0

    eff = effective_duration(bond, ytm, settlement)
    assert float(eff) == pytest.approx(float(metrics.modified_duration), rel=0.2)


def test_risk_calculator_consistency(fixed_rate_2025_bond) -> None:
    bond = fixed_rate_2025_bond
    settlement = Date.from_ymd(2020, 6, 15)
    price = Price.new(Decimal("100"), bond.currency())
    ytm = BondPricer().yield_to_maturity(bond, price, settlement)

    calc = BondRiskCalculator(bond=bond, ytm=ytm, settlement_date=settlement)
    metrics = calc.all_metrics()

    assert metrics.macaulay_duration == macaulay_duration(bond, ytm, settlement)
    assert metrics.modified_duration == modified_duration(bond, ytm, settlement)
    assert metrics.convexity == analytical_convexity(bond, ytm, settlement)
