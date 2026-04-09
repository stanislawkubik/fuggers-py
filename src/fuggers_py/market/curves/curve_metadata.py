"""Shared metadata records for calibrated market curves."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class CurveObjective(str, Enum):
    """Common objective families for calibrated curves."""

    L1 = "L1"
    L2 = "L2"


@dataclass(frozen=True, slots=True)
class CurveDiagnostics:
    """Common calibration diagnostics shared by calibrated curve classes."""

    objective_value: Decimal
    iterations: int
    converged: bool
    observation_count: int
    parameter_count: int


__all__ = [
    "CurveDiagnostics",
    "CurveObjective",
]
