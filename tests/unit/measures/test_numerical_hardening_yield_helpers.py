from __future__ import annotations

from decimal import Decimal

import pytest

import fuggers_py.pricers.bonds.yield_engine as yield_engine_module

from fuggers_py.measures.cashflows.irregular import IrregularPeriodHandler
from fuggers_py.measures.errors import AnalyticsError
from fuggers_py.measures.yields.street import street_convention_yield
from fuggers_py.products.bonds.instruments import FixedBondBuilder
from fuggers_py.pricers.bonds.yield_engine import StandardYieldEngine, _prepare_cashflows
from fuggers_py.reference.bonds.types import YieldCalculationRules
from fuggers_py.core import Currency, Date, Frequency
from fuggers_py.core.daycounts import ActActIcma, DayCountConvention
from fuggers_py.math.errors import ConvergenceFailed


def _treasury_bond():
    return (
        FixedBondBuilder.new()
        .with_issue_date(Date.from_ymd(2024, 1, 1))
        .with_maturity_date(Date.from_ymd(2025, 7, 1))
        .with_coupon_rate(Decimal("0.04"))
        .with_frequency(Frequency.SEMI_ANNUAL)
        .with_currency(Currency.USD)
        .with_rules(YieldCalculationRules.us_treasury())
        .build()
    )


def test_prepare_cashflows_accumulates_partial_icma_periods_from_settlement() -> None:
    bond = _treasury_bond()
    settlement = Date.from_ymd(2024, 4, 1)
    prepared = _prepare_cashflows(
        bond.cash_flows(),
        settlement_date=settlement,
        rules=bond.rules(),
    )

    icma = ActActIcma.semi_annual()
    first = bond.cash_flows()[0]
    assert first.accrual_start is not None
    assert first.accrual_end is not None
    first_period = icma.year_fraction_with_period(
        settlement,
        first.accrual_end,
        first.accrual_start,
        first.accrual_end,
    )

    assert prepared[0].years == pytest.approx(float(first_period), abs=1e-12)
    assert prepared[1].years == pytest.approx(prepared[0].years + 0.5, abs=1e-12)
    assert prepared[2].years == pytest.approx(prepared[1].years + 0.5, abs=1e-12)


def test_standard_yield_engine_dirty_price_is_monotone_in_yield() -> None:
    bond = _treasury_bond()
    engine = StandardYieldEngine()
    settlement = Date.from_ymd(2024, 4, 1)

    low = engine.dirty_price_from_yield(bond.cash_flows(), yield_rate=0.03, settlement_date=settlement, rules=bond.rules())
    mid = engine.dirty_price_from_yield(bond.cash_flows(), yield_rate=0.05, settlement_date=settlement, rules=bond.rules())
    high = engine.dirty_price_from_yield(bond.cash_flows(), yield_rate=0.08, settlement_date=settlement, rules=bond.rules())

    assert low > mid > high > 0.0


def test_standard_yield_engine_falls_back_to_brent_when_newton_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    bond = _treasury_bond()
    settlement = Date.from_ymd(2024, 4, 1)
    pricing_engine = StandardYieldEngine()
    dirty = Decimal(
        str(
            pricing_engine.dirty_price_from_yield(
                bond.cash_flows(),
                yield_rate=0.05,
                settlement_date=settlement,
                rules=bond.rules(),
            )
        )
    )
    clean = dirty - bond.accrued_interest(settlement)

    def _fail_newton(*_args, **_kwargs):
        raise ConvergenceFailed(iterations=1, residual=1.0)

    monkeypatch.setattr(yield_engine_module, "newton_raphson", _fail_newton)

    result = StandardYieldEngine().yield_from_price(
        bond.cash_flows(),
        clean_price=clean,
        accrued=bond.accrued_interest(settlement),
        settlement_date=settlement,
        rules=bond.rules(),
    )

    assert result.method == "Brent"
    assert result.yield_rate == pytest.approx(0.05, abs=1e-10)


def test_standard_yield_engine_surfaces_failure_after_all_solver_paths_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bond = _treasury_bond()
    settlement = Date.from_ymd(2024, 4, 1)

    def _fail_newton(*_args, **_kwargs):
        raise ConvergenceFailed(iterations=1, residual=1.0)

    def _fail_brent(*_args, **_kwargs):
        raise ConvergenceFailed(iterations=2, residual=1.0)

    monkeypatch.setattr(yield_engine_module, "newton_raphson", _fail_newton)
    monkeypatch.setattr(yield_engine_module, "brent", _fail_brent)

    with pytest.raises(yield_engine_module.YieldConvergenceFailed):
        StandardYieldEngine().yield_from_price(
            bond.cash_flows(),
            clean_price=Decimal("99.50"),
            accrued=bond.accrued_interest(settlement),
            settlement_date=settlement,
            rules=bond.rules(),
        )


def test_street_convention_yield_recovers_known_solution_and_moves_inverse_to_price() -> None:
    cashflows = [2.5, 102.5]
    times = [0.5, 1.0]
    expected_yield = 0.045
    dirty_price = sum(
        cf / ((1.0 + expected_yield / 2.0) ** (t * 2.0))
        for cf, t in zip(cashflows, times, strict=True)
    )

    solved = street_convention_yield(
        dirty_price,
        cashflows,
        times,
        frequency=2,
        initial_guess=-0.25,
    )
    richer = street_convention_yield(dirty_price + 0.5, cashflows, times, frequency=2)

    assert solved == pytest.approx(expected_yield, abs=1e-12)
    assert richer < solved


def test_irregular_period_handler_uses_day_count_objects_consistently() -> None:
    handler = IrregularPeriodHandler.new(DayCountConvention.ACT_365_FIXED)
    start = Date.from_ymd(2024, 1, 1)
    end = Date.from_ymd(2024, 2, 1)

    assert handler.days_between(start, end) == 31
    assert handler.year_fraction(start, end) == pytest.approx(float(Decimal(31) / Decimal(365)), abs=1e-12)
    assert handler.annual_factor(start, end) == pytest.approx(float(Decimal(365) / Decimal(31)), abs=1e-12)

    with pytest.raises(AnalyticsError, match="must be positive"):
        handler.annual_factor(start, start)
