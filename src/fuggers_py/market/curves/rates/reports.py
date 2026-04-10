"""Internal home for curve calibration and fit reports."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CalibrationPoint:
    """One calibration row for one input observation.

    The point stores the observed input value, the fitted value implied by the
    built curve, and the residual between them. Later instrument-specific
    reports can build on this without changing the core report shape.
    """

    instrument_id: str
    tenor: float
    observed_value: float
    fitted_value: float
    residual: float
    observed_kind: str
    weight: float = 1.0
    solver_iterations: int = 0


@dataclass(frozen=True, slots=True)
class CalibrationReport:
    """Immutable calibration report attached to one built yield curve."""

    converged: bool = True
    objective: str | None = None
    iterations: int = 0
    max_abs_residual: float = 0.0
    points: tuple[CalibrationPoint, ...] = ()
    solver: str | None = None


__all__ = [
    "CalibrationPoint",
    "CalibrationReport",
]
