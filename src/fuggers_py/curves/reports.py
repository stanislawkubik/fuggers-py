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
    curve_only_value: float | None = None
    regressor_values: tuple[float, ...] = ()
    regressor_contribution: float | None = None
    price_residual: float | None = None
    observed_ytm: float | None = None
    modeled_ytm: float | None = None
    ytm_residual: float | None = None
    ytm_bp_residual: float | None = None


@dataclass(frozen=True, slots=True)
class CalibrationReport:
    """Immutable calibration report attached to one built yield curve.

    Global-fit reports can also store the profiled regressor coefficient
    vector. ``regressor_coefficients`` stays aligned to ``regressors``.
    """

    converged: bool = True
    method: str | None = None
    objective: str | None = None
    iterations: int = 0
    max_abs_residual: float = 0.0
    points: tuple[CalibrationPoint, ...] = ()
    solver: str | None = None
    regressors: tuple[str, ...] = ()
    regressor_coefficients: tuple[float, ...] = ()
    kernel: str | None = None
    kernel_parameters: tuple[float, ...] = ()
    objective_value: float = 0.0


__all__ = [
    "CalibrationPoint",
    "CalibrationReport",
]
