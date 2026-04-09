"""Scenario bump helpers.

Scenario bumps interpolate raw decimal zero-rate shocks across a tenor grid
and apply the resulting shift in continuous compounding terms.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.reference.bonds.types import Tenor
from fuggers_py.core.traits import YieldCurve
from fuggers_py.core.types import Compounding, Date, Yield

from ..conversion import ValueConverter


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _tenor_to_years(tenor: Tenor | float) -> float:
    if isinstance(tenor, Tenor):
        return float(tenor.to_years_approx())
    return float(tenor)


def _tenor_from_date(reference_date: Date, date: Date) -> float:
    return float(reference_date.days_between(date)) / 365.0


@dataclass(frozen=True, slots=True)
class Scenario:
    """Piecewise-linear raw decimal bump scenario."""

    tenors: list[Tenor]
    bumps: list[float]

    def __post_init__(self) -> None:
        if len(self.tenors) != len(self.bumps):
            raise ValueError("Scenario tenors and bumps must have the same length.")
        if not self.tenors:
            raise ValueError("Scenario must define at least one node.")
        years = [float(t.to_years_approx()) for t in self.tenors]
        if sorted(years) != years:
            raise ValueError("Scenario tenors must be sorted ascending.")
        if len(set(years)) != len(years):
            raise ValueError("Scenario tenors must not contain duplicates.")

    def bump_at(self, tenor: Tenor | float) -> float:
        """Return the interpolated raw decimal bump at ``tenor``."""
        t = _tenor_to_years(tenor)
        years = [float(x.to_years_approx()) for x in self.tenors]
        bumps = list(self.bumps)

        if t <= years[0]:
            return float(bumps[0])
        if t >= years[-1]:
            return float(bumps[-1])

        for i in range(1, len(years)):
            if years[i - 1] <= t <= years[i]:
                t0 = years[i - 1]
                t1 = years[i]
                b0 = float(bumps[i - 1])
                b1 = float(bumps[i])
                if t1 == t0:
                    return float(b1)
                w = (t - t0) / (t1 - t0)
                return b0 + w * (b1 - b0)

        return float(bumps[-1])

    def apply(self, curve: YieldCurve) -> "ScenarioCurve":
        """Apply the bump scenario to a curve."""
        return ScenarioCurve(base_curve=curve, scenario=self)


@dataclass(frozen=True, slots=True)
class ScenarioCurve(YieldCurve):
    """Curve with a tenor-dependent scenario bump."""

    base_curve: YieldCurve
    scenario: Scenario

    def date(self) -> Date:
        """Return the date of the underlying curve."""
        return self.base_curve.date()

    def bump_at_tenor(self, t: float) -> float:
        """Return the scenario bump applied at tenor ``t``."""
        return self.scenario.bump_at(t)

    def zero_rate(self, date: Date) -> Yield:
        """Return the continuously compounded bumped zero rate."""
        base_zero = self.base_curve.zero_rate(date).convert_to(Compounding.CONTINUOUS).value()
        t = _tenor_from_date(self.date(), date)
        bumped = float(base_zero) + self.scenario.bump_at(t)
        return Yield.new(_to_decimal(bumped), Compounding.CONTINUOUS)

    def discount_factor(self, date: Date) -> Decimal:
        """Return the discount factor implied by the scenario bump."""
        t = _tenor_from_date(self.date(), date)
        if t <= 0.0:
            return Decimal(1)
        zero = self.zero_rate(date).value()
        df = ValueConverter.zero_to_df(float(zero), float(t), Compounding.CONTINUOUS)
        return _to_decimal(df)


def parallel_up_50bp() -> Scenario:
    """Return a +50 bp parallel scenario expressed in raw decimals."""
    return Scenario(
        tenors=[Tenor.parse("1Y"), Tenor.parse("30Y")],
        bumps=[0.005, 0.005],
    )


def parallel_down_50bp() -> Scenario:
    """Return a -50 bp parallel scenario expressed in raw decimals."""
    return Scenario(
        tenors=[Tenor.parse("1Y"), Tenor.parse("30Y")],
        bumps=[-0.005, -0.005],
    )


def steepener_50bp() -> Scenario:
    """Return a 50 bp steepener scenario."""
    return Scenario(
        tenors=[Tenor.parse("2Y"), Tenor.parse("30Y")],
        bumps=[-0.005, 0.005],
    )


def flattener_50bp() -> Scenario:
    """Return a 50 bp flattener scenario."""
    return Scenario(
        tenors=[Tenor.parse("2Y"), Tenor.parse("30Y")],
        bumps=[0.005, -0.005],
    )


__all__ = [
    "Scenario",
    "ScenarioCurve",
    "parallel_up_50bp",
    "parallel_down_50bp",
    "steepener_50bp",
    "flattener_50bp",
]
