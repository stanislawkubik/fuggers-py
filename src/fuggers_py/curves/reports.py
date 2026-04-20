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
class GlobalFitPoint(CalibrationPoint):
    """One global-fit row with curve-only and bond diagnostic detail.

    ``residual`` stays in the native optimization target units. Bond YTM
    fields are diagnostics only and do not change the optimization target.
    """

    curve_only_value: float = 0.0
    regressor_values: tuple[float, ...] = ()
    regressor_contribution: float = 0.0
    price_residual: float | None = None
    observed_ytm: float | None = None
    modeled_ytm: float | None = None
    ytm_residual: float | None = None
    ytm_bp_residual: float | None = None


@dataclass(frozen=True, slots=True)
class CalibrationReport:
    """Immutable calibration report attached to one built yield curve.

    Global-fit reports can also store the profiled regressor coefficient
    vector. ``regressor_coefficients`` stays aligned to ``regressor_names``.
    """

    converged: bool = True
    objective: str | None = None
    iterations: int = 0
    max_abs_residual: float = 0.0
    points: tuple[CalibrationPoint, ...] = ()
    solver: str | None = None
    regressor_names: tuple[str, ...] = ()
    regressor_coefficients: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class GlobalFitReport(CalibrationReport):
    """CalibrationReport extension for one imperfect global regression fit.

    ``fitted_kernel_parameters`` stores the raw fitted kernel parameters:
    knot zero values for cubic spline, beta/tau values for Nelson-Siegel and
    Svensson, and coefficients for exponential spline. ``residuals`` stores
    the typed per-row residual details and is also mirrored in ``points`` for
    the shared report interface.
    """

    kernel_kind: str | None = None
    fitted_kernel_parameters: tuple[float, ...] = ()
    objective_value: float = 0.0
    residuals: tuple[GlobalFitPoint, ...] = ()


__all__ = [
    "CalibrationPoint",
    "CalibrationReport",
    "GlobalFitPoint",
    "GlobalFitReport",
]
