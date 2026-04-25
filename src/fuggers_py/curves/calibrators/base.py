"""Shared internal calibrator contracts for rate-curve fitting."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from ..errors import InvalidCurveInput
from ..kernels.base import CurveKernel, KernelSpec
from ..reports import CalibrationReport
from ..spec import CurveSpec

_METHODS = frozenset({"bootstrap", "global_fit"})
_OBJECTIVES = frozenset({"exact_fit", "weighted_l2"})
_DEFAULT_OBJECTIVE_BY_METHOD = {
    "bootstrap": "exact_fit",
    "global_fit": "weighted_l2",
}
_BOND_TARGETS = frozenset({"dirty_price", "clean_price"})


def _normalize_choice(value: object, *, field_name: str, allowed: frozenset[str]) -> str:
    if not isinstance(value, str):
        raise InvalidCurveInput(f"CalibrationSpec.{field_name} must be a string.")
    normalized = value.strip().lower()
    if normalized not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise InvalidCurveInput(f"CalibrationSpec.{field_name} must be one of: {allowed_text}.")
    return normalized


@dataclass(frozen=True, slots=True)
class CalibrationSpec:
    """Single fit-control object for one quote-driven curve calibration.

    ``regressors`` defines the column order used when normalized bond
    quote rows align ``BondQuote.regressors`` into ``QuoteRow.regressor_values``.
    """

    method: str = "bootstrap"
    objective: str | None = None
    regressors: tuple[str, ...] = ()
    bond_target: str = "dirty_price"

    def __post_init__(self) -> None:
        method = _normalize_choice(self.method, field_name="method", allowed=_METHODS)
        object.__setattr__(self, "method", method)

        objective = self.objective
        if objective is None:
            normalized_objective = _DEFAULT_OBJECTIVE_BY_METHOD[method]
        else:
            normalized_objective = _normalize_choice(objective, field_name="objective", allowed=_OBJECTIVES)
        if method == "bootstrap" and normalized_objective != "exact_fit":
            raise InvalidCurveInput("CalibrationSpec.method='bootstrap' requires objective='exact_fit'.")
        if method == "global_fit" and normalized_objective != "weighted_l2":
            raise InvalidCurveInput("CalibrationSpec.method='global_fit' requires objective='weighted_l2'.")
        object.__setattr__(self, "objective", normalized_objective)

        regressors = self.regressors
        if isinstance(regressors, str):
            raise InvalidCurveInput("CalibrationSpec.regressors must be an iterable of strings, not one string.")
        try:
            normalized_regressors = tuple(regressors)
        except TypeError as exc:
            raise InvalidCurveInput("CalibrationSpec.regressors must be an iterable of strings.") from exc
        if any(not isinstance(name, str) for name in normalized_regressors):
            raise InvalidCurveInput("CalibrationSpec.regressors must contain only strings.")
        object.__setattr__(self, "regressors", normalized_regressors)
        object.__setattr__(
            self,
            "bond_target",
            _normalize_choice(self.bond_target, field_name="bond_target", allowed=_BOND_TARGETS),
        )


def _require_bootstrap_calibration_spec(calibration_spec: CalibrationSpec) -> CalibrationSpec:
    if not isinstance(calibration_spec, CalibrationSpec):
        raise InvalidCurveInput("BootstrapCalibrator requires calibration_spec to be a CalibrationSpec.")
    if calibration_spec.method != "bootstrap":
        raise InvalidCurveInput("BootstrapCalibrator requires calibration_spec.method == 'bootstrap'.")
    if calibration_spec.regressors:
        raise InvalidCurveInput("BootstrapCalibrator does not accept calibration_spec.regressors.")
    if calibration_spec.objective != "exact_fit":
        raise InvalidCurveInput("BootstrapCalibrator requires calibration_spec.objective == 'exact_fit'.")
    return calibration_spec


def _require_global_fit_calibration_spec(calibration_spec: CalibrationSpec) -> CalibrationSpec:
    if not isinstance(calibration_spec, CalibrationSpec):
        raise InvalidCurveInput("GlobalFitCalibrator requires calibration_spec to be a CalibrationSpec.")
    if calibration_spec.method != "global_fit":
        raise InvalidCurveInput("GlobalFitCalibrator requires calibration_spec.method == 'global_fit'.")
    if calibration_spec.objective == "exact_fit":
        raise InvalidCurveInput("GlobalFitCalibrator does not support objective='exact_fit'.")
    if calibration_spec.objective != "weighted_l2":
        raise InvalidCurveInput("GlobalFitCalibrator requires calibration_spec.objective == 'weighted_l2'.")
    return calibration_spec


class CurveCalibrator(ABC):
    """Internal calibrator contract for building one fitted curve kernel."""

    @abstractmethod
    def fit(
        self,
        quotes: Sequence[object],
        *,
        spec: CurveSpec,
        kernel_spec: KernelSpec,
    ) -> tuple[CurveKernel, CalibrationReport]:
        """Build one kernel plus one calibration report from market quotes."""


__all__ = [
    "CalibrationSpec",
    "CurveCalibrator",
]
