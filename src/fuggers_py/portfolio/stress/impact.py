"""Stress impact helpers."""

from __future__ import annotations

from decimal import Decimal

from ..analytics.base import PortfolioAnalytics
from ..portfolio import Portfolio
from ..types import StressResult
from .scenarios import KeyRateShiftScenario, RateShockScenario, SpreadShockScenario, StressSummary, summarize_results


def _run_stress_result(portfolio: Portfolio, *, curve, settlement_date, scenario: object) -> tuple[str, StressResult] | None:
    if isinstance(scenario, RateShockScenario):
        return (
            scenario.name,
            rate_shock_impact(
                portfolio,
                curve=curve,
                settlement_date=settlement_date,
                bump_bps=scenario.bump_bps,
                scenario_name=scenario.name,
            ),
        )
    if isinstance(scenario, SpreadShockScenario):
        return (
            scenario.name,
            spread_shock_result(
                portfolio,
                curve=curve,
                settlement_date=settlement_date,
                bump_bps=scenario.bump_bps,
                scenario_name=scenario.name,
            ),
        )
    if isinstance(scenario, KeyRateShiftScenario):
        return (
            scenario.name,
            key_rate_shift_result(
                portfolio,
                curve=curve,
                settlement_date=settlement_date,
                tenor_shocks_bps=scenario.tenor_shocks_bps,
                scenario_name=scenario.name,
            ),
        )
    return None


def rate_shock_impact(
    portfolio: Portfolio,
    *,
    curve,
    settlement_date,
    bump_bps: Decimal,
    scenario_name: str | None = None,
) -> StressResult:
    """Return the dirty-PV change for a parallel rate shock in bps."""

    metrics = PortfolioAnalytics(portfolio).metrics(curve, settlement_date)
    positions = PortfolioAnalytics(portfolio).position_metrics(curve, settlement_date)
    actual_change = -(metrics.dv01 * bump_bps)
    return StressResult(
        base_dirty_pv=metrics.dirty_pv,
        stressed_dirty_pv=metrics.dirty_pv + actual_change,
        actual_change=actual_change,
        dv01_approximation=actual_change,
        scenario_name=scenario_name or f"parallel_{bump_bps}",
        breakdown={item.name: -(item.dv01 * bump_bps) for item in positions},
    )


def parallel_shift_impact(
    portfolio: Portfolio,
    *,
    curve,
    settlement_date,
    bump_bps: Decimal,
    scenario_name: str | None = None,
) -> StressResult:
    """Compatibility alias for :func:`rate_shock_impact`."""

    return rate_shock_impact(
        portfolio,
        curve=curve,
        settlement_date=settlement_date,
        bump_bps=bump_bps,
        scenario_name=scenario_name,
    )


def spread_shock_impact(portfolio: Portfolio, *, curve, settlement_date, bump_bps: Decimal) -> Decimal:
    """Return the dirty-PV change for a parallel spread shock in bps."""

    metrics = PortfolioAnalytics(portfolio).metrics(curve, settlement_date)
    return -(metrics.cs01 * bump_bps)


def key_rate_shift_impact(portfolio: Portfolio, *, curve, settlement_date, tenor_shocks_bps: dict[str, Decimal]) -> Decimal:
    """Return the dirty-PV change for tenor-specific key-rate shocks."""

    profile = PortfolioAnalytics(portfolio).metrics(curve, settlement_date).key_rate_profile
    return sum((profile.get(tenor, Decimal(0)) * shock for tenor, shock in tenor_shocks_bps.items()), Decimal(0))


def spread_shock_result(
    portfolio: Portfolio,
    *,
    curve,
    settlement_date,
    bump_bps: Decimal,
    scenario_name: str | None = None,
) -> StressResult:
    """Return a typed result for a parallel spread shock."""

    metrics = PortfolioAnalytics(portfolio).metrics(curve, settlement_date)
    change = spread_shock_impact(portfolio, curve=curve, settlement_date=settlement_date, bump_bps=bump_bps)
    positions = PortfolioAnalytics(portfolio).position_metrics(curve, settlement_date)
    return StressResult(
        base_dirty_pv=metrics.dirty_pv,
        stressed_dirty_pv=metrics.dirty_pv + change,
        actual_change=change,
        dv01_approximation=Decimal(0),
        scenario_name=scenario_name or f"spread_{bump_bps}",
        breakdown={item.name: -((item.cs01 or Decimal(0)) * bump_bps) for item in positions},
    )


def key_rate_shift_result(
    portfolio: Portfolio,
    *,
    curve,
    settlement_date,
    tenor_shocks_bps: dict[str, Decimal],
    scenario_name: str | None = None,
) -> StressResult:
    """Return a typed result for a key-rate shift scenario."""

    metrics = PortfolioAnalytics(portfolio).metrics(curve, settlement_date)
    change = key_rate_shift_impact(
        portfolio,
        curve=curve,
        settlement_date=settlement_date,
        tenor_shocks_bps=tenor_shocks_bps,
    )
    return StressResult(
        base_dirty_pv=metrics.dirty_pv,
        stressed_dirty_pv=metrics.dirty_pv + change,
        actual_change=change,
        dv01_approximation=sum((metrics.key_rate_profile.get(key, Decimal(0)) * value for key, value in tenor_shocks_bps.items()), Decimal(0)),
        scenario_name=scenario_name or "key_rate_shift",
        breakdown=dict(metrics.key_rate_profile),
    )


def run_stress_scenarios(portfolio: Portfolio, *, curve, settlement_date, scenarios: list[object]) -> StressSummary:
    """Run a list of stress scenarios and return a summary."""

    results: dict[str, StressResult] = {}
    for scenario in scenarios:
        resolved = _run_stress_result(portfolio, curve=curve, settlement_date=settlement_date, scenario=scenario)
        if resolved is None:
            continue
        name, result = resolved
        results[name] = result
    return summarize_results(results)


def run_stress_scenario(portfolio: Portfolio, *, curve, settlement_date, scenario: object) -> StressResult:
    """Run a single stress scenario and return its result."""

    resolved = _run_stress_result(portfolio, curve=curve, settlement_date=settlement_date, scenario=scenario)
    if resolved is None:
        raise TypeError(f"Unsupported stress scenario: {scenario!r}")
    return resolved[1]


def stress_scenarios(portfolio: Portfolio, *, curve, settlement_date, scenarios: list[object]) -> StressSummary:
    """Compatibility alias for :func:`run_stress_scenarios`."""

    return run_stress_scenarios(portfolio, curve=curve, settlement_date=settlement_date, scenarios=scenarios)


__all__ = [
    "key_rate_shift_impact",
    "key_rate_shift_result",
    "parallel_shift_impact",
    "rate_shock_impact",
    "run_stress_scenario",
    "run_stress_scenarios",
    "spread_shock_impact",
    "spread_shock_result",
    "stress_scenarios",
]
