from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.bonds.yields import (
    StandardYieldEngine,
    YieldSolver,
    bond_equivalent_yield,
    cd_equivalent_yield,
    discount_yield,
    money_market_yield,
)
from fuggers_py._core import YieldCalculationRules
from fuggers_py._core import Date


def test_yield_engine_roundtrip(fixed_rate_2025_bond) -> None:
    bond = fixed_rate_2025_bond
    engine = StandardYieldEngine()
    rules = bond.rules()
    settlement = Date.from_ymd(2020, 6, 15)
    clean_price = Decimal("105")
    accrued = bond.accrued_interest(settlement)

    result = engine.yield_from_price(
        bond.cash_flows(),
        clean_price=clean_price,
        accrued=accrued,
        settlement_date=settlement,
        rules=rules,
    )
    dirty = engine.dirty_price_from_yield(
        bond.cash_flows(),
        yield_rate=result.yield_value,
        settlement_date=settlement,
        rules=rules,
    )
    clean_back = dirty - float(accrued)
    assert clean_back == pytest.approx(float(clean_price), abs=1e-3)


def test_par_bond_yield_matches_coupon(fixed_rate_2025_bond) -> None:
    bond = fixed_rate_2025_bond
    engine = StandardYieldEngine()
    settlement = Date.from_ymd(2020, 6, 15)
    clean_price = Decimal("100")
    accrued = bond.accrued_interest(settlement)
    res = engine.yield_from_price(
        bond.cash_flows(),
        clean_price=clean_price,
        accrued=accrued,
        settlement_date=settlement,
        rules=bond.rules(),
    )
    assert res.yield_value == pytest.approx(0.075, abs=1e-3)


def test_yield_result_helpers() -> None:
    solver = YieldSolver()
    cashflows = [5.0, 105.0]
    times = [0.5, 1.0]
    res = solver.solve(dirty_price=100.0, cashflows=cashflows, times=times, frequency=2)
    assert res.yield_decimal() == pytest.approx(res.yield_value, abs=1e-12)
    assert res.yield_percent() == pytest.approx(res.yield_value * 100.0, abs=1e-10)


def test_standard_engine_rules_convention(fixed_rate_2025_bond) -> None:
    bond = fixed_rate_2025_bond
    engine = StandardYieldEngine()
    rules = YieldCalculationRules.us_treasury()
    settlement = Date.from_ymd(2020, 6, 15)
    accrued = bond.accrued_interest(settlement)
    res = engine.yield_from_price(
        bond.cash_flows(),
        clean_price=Decimal("105"),
        accrued=accrued,
        settlement_date=settlement,
        rules=rules,
    )
    assert res.convention == rules.convention


def test_solver_fallback_robustness(fixed_rate_2025_bond) -> None:
    bond = fixed_rate_2025_bond
    engine = StandardYieldEngine()
    settlement = Date.from_ymd(2020, 6, 15)
    accrued = bond.accrued_interest(settlement)
    res = engine.yield_from_price(
        bond.cash_flows(),
        clean_price=Decimal("60"),
        accrued=accrued,
        settlement_date=settlement,
        rules=bond.rules(),
    )
    assert res.converged


def test_money_market_helpers() -> None:
    disc = discount_yield(100, 98, 90)
    bey = bond_equivalent_yield(100, 98, 90)
    cd = cd_equivalent_yield(100, 98, 90)
    mm = money_market_yield(100, 98, 90)
    assert float(disc) > 0
    assert float(bey) > 0
    assert float(cd) > 0
    assert float(mm) > 0
