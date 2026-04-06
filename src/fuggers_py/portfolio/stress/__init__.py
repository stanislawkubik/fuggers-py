"""Stress-testing helpers.

The stress surface applies rate, spread, and key-rate shocks to a portfolio
and returns dirty-PV changes with the package's sign convention
(``portfolio`` minus ``stressed``).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..portfolio import Portfolio
from ..types import StressResult
from .impact import (
    key_rate_shift_impact,
    key_rate_shift_result,
    parallel_shift_impact,
    rate_shock_impact,
    run_stress_scenario,
    run_stress_scenarios,
    spread_shock_impact,
    spread_shock_result,
    stress_scenarios,
)
from .scenarios import (
    KeyRateShiftScenario,
    RateScenario,
    RateShockScenario,
    SpreadScenario,
    SpreadShockScenario,
    StressScenario,
    StressSummary,
    TenorShift,
    best_case,
    summarize_results,
    standard_scenarios,
    worst_case,
)


@dataclass(frozen=True, slots=True)
class Stress:
    """Convenience wrapper around portfolio stress helpers."""

    portfolio: Portfolio

    def parallel_shift(self, curve, settlement_date, *, bump_bps):
        """Return the dirty-PV change for a parallel rate shift in bps."""

        return rate_shock_impact(self.portfolio, curve=curve, settlement_date=settlement_date, bump_bps=bump_bps)


__all__ = [
    "KeyRateShiftScenario",
    "RateScenario",
    "RateShockScenario",
    "SpreadScenario",
    "SpreadShockScenario",
    "Stress",
    "StressScenario",
    "StressSummary",
    "TenorShift",
    "best_case",
    "key_rate_shift_impact",
    "key_rate_shift_result",
    "parallel_shift_impact",
    "rate_shock_impact",
    "run_stress_scenario",
    "run_stress_scenarios",
    "spread_shock_impact",
    "spread_shock_result",
    "summarize_results",
    "standard_scenarios",
    "stress_scenarios",
    "worst_case",
]
