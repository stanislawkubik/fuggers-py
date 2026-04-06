"""Curve bumping helpers for scenario analysis.

The exported helpers apply raw decimal zero-rate shifts in continuous
compounding terms. Parallel bumps shift the entire curve, key-rate bumps use a
localized triangular profile around an anchor tenor, and scenario bumps define
piecewise-linear shock surfaces across a tenor grid. The standard key-tenor set
is exposed as :data:`STANDARD_KEY_TENORS` for common 3M to 30Y analysis.
"""

from __future__ import annotations

from fuggers_py.reference.bonds.types import Tenor

from .key_rate import KeyRateBump, KeyRateBumpedCurve
from .parallel import BumpedCurve, ParallelBump
from .scenario import (
    Scenario,
    ScenarioCurve,
    flattener_50bp,
    parallel_down_50bp,
    parallel_up_50bp,
    steepener_50bp,
)

ScenarioBump = Scenario
ArcBumpedCurve = BumpedCurve
ArcKeyRateBumpedCurve = KeyRateBumpedCurve
ArcScenarioCurve = ScenarioCurve
STANDARD_KEY_TENORS = (
    Tenor.parse("3M"),
    Tenor.parse("6M"),
    Tenor.parse("1Y"),
    Tenor.parse("2Y"),
    Tenor.parse("3Y"),
    Tenor.parse("5Y"),
    Tenor.parse("7Y"),
    Tenor.parse("10Y"),
    Tenor.parse("20Y"),
    Tenor.parse("30Y"),
)


def key_rate_profile(
    key_tenor: Tenor,
    *,
    tenors: tuple[Tenor, ...] = STANDARD_KEY_TENORS,
    bump: float = 1e-4,
) -> dict[Tenor, float]:
    """Return the key-rate bump profile on the supplied tenor grid.

    Parameters
    ----------
    key_tenor:
        Anchor tenor that receives the full raw decimal bump.
    tenors:
        Ordered tenor grid used to construct the localized triangular profile.
    bump:
        Raw decimal zero-rate bump. ``1e-4`` corresponds to 1 bp.

    Returns
    -------
    dict[Tenor, float]
        Mapping from each tenor to its bumped raw decimal zero-rate shift.
    """
    scenario = KeyRateBump(list(tenors), key_tenor, bump)
    return {tenor: float(scenario.bump_at(tenor)) for tenor in tenors}

__all__ = [
    "ParallelBump",
    "KeyRateBump",
    "Scenario",
    "ScenarioBump",
    "BumpedCurve",
    "KeyRateBumpedCurve",
    "ScenarioCurve",
    "ArcBumpedCurve",
    "ArcKeyRateBumpedCurve",
    "ArcScenarioCurve",
    "STANDARD_KEY_TENORS",
    "key_rate_profile",
    "parallel_up_50bp",
    "parallel_down_50bp",
    "steepener_50bp",
    "flattener_50bp",
]
