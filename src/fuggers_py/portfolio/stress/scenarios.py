"""Stress scenario definitions.

The scenario layer keeps named rate, spread, and key-rate shocks separate from
the stress runners so portfolios can be evaluated against reusable templates.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import replace
from dataclasses import dataclass
from decimal import Decimal

from ..types import StressResult


@dataclass(frozen=True, slots=True)
class StressScenario:
    """Base class for a named stress scenario."""

    name: str


@dataclass(frozen=True, slots=True)
class RateShockScenario(StressScenario):
    """Parallel rate shock measured in basis points."""

    bump_bps: Decimal


@dataclass(frozen=True, slots=True)
class SpreadShockScenario(StressScenario):
    """Parallel spread shock measured in basis points."""

    bump_bps: Decimal


@dataclass(frozen=True, slots=True)
class TenorShift:
    """A single key-rate tenor shock in basis points."""

    tenor: str
    bump_bps: Decimal


@dataclass(frozen=True, slots=True)
class KeyRateShiftScenario(StressScenario):
    """Collection of tenor-specific basis-point shocks."""

    tenor_shocks_bps: dict[str, Decimal]

    @property
    def tenor_shifts(self) -> tuple[TenorShift, ...]:
        """Return the tenor shocks as typed objects."""

        return tuple(TenorShift(tenor=tenor, bump_bps=shock) for tenor, shock in self.tenor_shocks_bps.items())

    @classmethod
    def from_tenor_shifts(cls, name: str, shifts: tuple[TenorShift, ...] | list[TenorShift]) -> "KeyRateShiftScenario":
        """Build a scenario from typed tenor shifts."""

        return cls(name=name, tenor_shocks_bps={shift.tenor: shift.bump_bps for shift in shifts})


@dataclass(frozen=True, slots=True)
class StressSummary(Mapping[str, StressResult]):
    """Mapping of scenario names to stress results."""

    results: dict[str, StressResult]

    @classmethod
    def from_results(
        cls,
        results: "StressSummary | Mapping[str, StressResult] | Iterable[StressResult]",
    ) -> "StressSummary":
        """Normalize a collection of stress results into a summary."""

        if isinstance(results, cls):
            return results

        named_results: dict[str, StressResult] = {}
        if isinstance(results, Mapping):
            iterator = results.items()
        else:
            iterator = (
                (
                    result.scenario_name or f"scenario_{index}",
                    result,
                )
                for index, result in enumerate(results, start=1)
            )

        for index, (name, result) in enumerate(iterator, start=1):
            scenario_name = result.scenario_name or name or f"scenario_{index}"
            if result.scenario_name == scenario_name:
                named_results[scenario_name] = result
            else:
                named_results[scenario_name] = replace(result, scenario_name=scenario_name)
        return cls(results=named_results)

    def __getitem__(self, key: str) -> StressResult:
        return self.results[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.results)

    def __len__(self) -> int:
        return len(self.results)

    @property
    def scenario_count(self) -> int:
        """Return the number of scenarios in the summary."""

        return len(self.results)

    @property
    def aggregate_change(self) -> Decimal:
        """Return the sum of all scenario PV changes."""

        return sum((result.actual_change for result in self.results.values()), Decimal(0))

    @property
    def worst_loss(self) -> Decimal:
        """Return the most negative PV change."""

        return min((result.actual_change for result in self.results.values()), default=Decimal(0))

    @property
    def best_gain(self) -> Decimal:
        """Return the most positive PV change."""

        return max((result.actual_change for result in self.results.values()), default=Decimal(0))

    def best_case(self) -> StressResult | None:
        """Return the scenario with the largest PV change."""

        if not self.results:
            return None
        return max(self.results.values(), key=lambda result: result.actual_change)

    def worst_case(self) -> StressResult | None:
        """Return the scenario with the smallest PV change."""

        if not self.results:
            return None
        return min(self.results.values(), key=lambda result: result.actual_change)


RateScenario = RateShockScenario
SpreadScenario = SpreadShockScenario


def standard_scenarios() -> list[StressScenario]:
    """Return the standard set of illustrative stress scenarios."""

    return [
        RateShockScenario(name="+10bps parallel", bump_bps=Decimal("10")),
        RateShockScenario(name="-10bps parallel", bump_bps=Decimal("-10")),
        SpreadShockScenario(name="+25bps spread widening", bump_bps=Decimal("25")),
        KeyRateShiftScenario(
            name="2s10s steepener",
            tenor_shocks_bps={"2Y": Decimal("-10"), "5Y": Decimal("5"), "10Y": Decimal("10")},
        ),
    ]


def summarize_results(
    results: StressSummary | Mapping[str, StressResult] | Iterable[StressResult],
) -> StressSummary:
    """Normalize stress results into a :class:`StressSummary`."""

    return StressSummary.from_results(results)


def best_case(
    results: StressSummary | Mapping[str, StressResult] | Iterable[StressResult],
) -> StressResult | None:
    """Return the best-case stress result, if any."""

    return summarize_results(results).best_case()


def worst_case(
    results: StressSummary | Mapping[str, StressResult] | Iterable[StressResult],
) -> StressResult | None:
    """Return the worst-case stress result, if any."""

    return summarize_results(results).worst_case()


__all__ = [
    "KeyRateShiftScenario",
    "RateScenario",
    "RateShockScenario",
    "SpreadScenario",
    "SpreadShockScenario",
    "StressScenario",
    "StressSummary",
    "TenorShift",
    "best_case",
    "summarize_results",
    "standard_scenarios",
    "worst_case",
]
