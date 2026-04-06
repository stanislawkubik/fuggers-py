from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.core import Date
from fuggers_py.portfolio import (
    AggregatedAttribution,
    AttributionInput,
    benchmark_comparison,
    duration_difference_by_sector,
    estimate_rate_returns,
    estimate_spread_returns,
    parallel_shift_impact,
    spread_difference_by_sector,
    spread_shock_impact,
)

from tests.helpers._portfolio_helpers import make_benchmark, make_curve, make_portfolio


pytestmark = pytest.mark.validation


def test_sector_active_differences_reconcile_to_benchmark_comparison() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    benchmark = make_benchmark(ref)
    curve = make_curve(ref)
    comparison = benchmark_comparison(portfolio, benchmark, curve, ref)

    assert float(duration_difference_by_sector(portfolio, benchmark, curve=curve, settlement_date=ref).total_active) == pytest.approx(
        float(comparison.active_duration)
    )
    assert float(spread_difference_by_sector(portfolio, benchmark, curve=curve, settlement_date=ref).total_active) == pytest.approx(
        float(comparison.active_z_spread)
    )


def test_aggregated_attribution_matches_component_and_stress_identities() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    benchmark = make_benchmark(ref)
    curve = make_curve(ref)
    assumptions = AttributionInput(
        income_horizon_years=Decimal("0.5"),
        rate_change_bps=Decimal("10"),
        spread_change_bps=Decimal("25"),
    )

    aggregated = AggregatedAttribution.from_portfolios(
        portfolio,
        curve=curve,
        settlement_date=ref,
        assumptions=assumptions,
        benchmark=benchmark,
    )
    metrics = parallel_shift_impact(portfolio, curve=curve, settlement_date=ref, bump_bps=Decimal("10"))
    spread_change = spread_shock_impact(portfolio, curve=curve, settlement_date=ref, bump_bps=Decimal("25"))

    assert abs(
        aggregated.active_total_return
        - (aggregated.active_income_return + aggregated.active_rate_return + aggregated.active_spread_return)
    ) <= Decimal("1e-24")
    assert estimate_rate_returns(portfolio, curve=curve, settlement_date=ref, assumptions=assumptions) == metrics.actual_change / metrics.base_dirty_pv
    assert estimate_spread_returns(portfolio, curve=curve, settlement_date=ref, assumptions=assumptions) == spread_change / metrics.base_dirty_pv
