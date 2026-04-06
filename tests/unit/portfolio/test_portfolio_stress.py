from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.core import Date
from fuggers_py.portfolio import (
    PortfolioBenchmark,
    calculate_portfolio_analytics,
    key_rate_shift_result,
    rate_shock_impact,
    run_stress_scenarios,
    spread_shock_result,
    standard_scenarios,
)

from tests.helpers._portfolio_helpers import make_curve, make_portfolio


def test_parallel_shift_stress_changes_pv_in_expected_direction() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    result = rate_shock_impact(make_portfolio(ref), curve=make_curve(ref), settlement_date=ref, bump_bps=Decimal("10"))
    assert result.actual_change < 0


def test_parallel_shift_pv_change_is_close_to_dv01_approximation() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    result = rate_shock_impact(portfolio, curve=make_curve(ref), settlement_date=ref, bump_bps=Decimal("10"))
    metrics = calculate_portfolio_analytics(portfolio, curve=make_curve(ref), settlement_date=ref)
    assert float(result.actual_change) == pytest.approx(float(-(metrics.dv01 * Decimal("10"))))


def test_key_rate_shock_returns_breakdown() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    result = key_rate_shift_result(
        make_portfolio(ref),
        curve=make_curve(ref),
        settlement_date=ref,
        tenor_shocks_bps={"2Y": Decimal("10"), "10Y": Decimal("-5")},
    )
    assert result.breakdown


def test_spread_shock_widens_credit_portfolio_losses() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    result = spread_shock_result(make_portfolio(ref), curve=make_curve(ref), settlement_date=ref, bump_bps=Decimal("25"))
    assert result.actual_change <= 0


def test_standard_scenarios_runner() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    results = run_stress_scenarios(make_portfolio(ref), curve=make_curve(ref), settlement_date=ref, scenarios=standard_scenarios())
    assert results
    assert "+10bps parallel" in results
