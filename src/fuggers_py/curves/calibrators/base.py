"""Shared internal calibrator contracts for rate-curve fitting."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto

from ..kernels import CurveKernel, KernelSpec
from ..reports import CalibrationReport
from ..spec import CurveSpec


class CalibrationObjective(Enum):
    """Objective convention for one curve calibration run."""

    EXACT_FIT = auto()
    WEIGHTED_L2 = auto()


class CalibrationMode(Enum):
    """Top-level fitting route for one calibration run."""

    BOOTSTRAP = auto()
    GLOBAL_FIT = auto()


class BondFitTarget(Enum):
    """Observed bond-value target used during calibration."""

    DIRTY_PRICE = auto()
    CLEAN_PRICE = auto()


class GlobalFitOptimizerKind(Enum):
    """Least-squares routine used by the global-fit calibrator."""

    LEVENBERG_MARQUARDT = auto()
    GAUSS_NEWTON = auto()


@dataclass(frozen=True, slots=True)
class CalibrationSpec:
    """Single fit-control object for one quote-driven curve calibration.

    ``regressor_names`` defines the column order used when normalized bond
    quote rows align ``BondQuote.regressors`` into ``QuoteRow.regressor_values``.
    """

    mode: CalibrationMode
    objective: CalibrationObjective
    regressor_names: tuple[str, ...] = ()
    bond_fit_target: BondFitTarget = BondFitTarget.DIRTY_PRICE

    def __post_init__(self) -> None:
        if not isinstance(self.mode, CalibrationMode):
            raise ValueError("CalibrationSpec.mode must be a CalibrationMode.")
        if not isinstance(self.objective, CalibrationObjective):
            raise ValueError("CalibrationSpec.objective must be a CalibrationObjective.")
        regressor_names = self.regressor_names
        if isinstance(regressor_names, str):
            raise ValueError("CalibrationSpec.regressor_names must be an iterable of strings, not one string.")
        try:
            normalized_regressor_names = tuple(regressor_names)
        except TypeError as exc:
            raise ValueError("CalibrationSpec.regressor_names must be an iterable of strings.") from exc
        if any(not isinstance(name, str) for name in normalized_regressor_names):
            raise ValueError("CalibrationSpec.regressor_names must contain only strings.")
        object.__setattr__(self, "regressor_names", normalized_regressor_names)
        if not isinstance(self.bond_fit_target, BondFitTarget):
            raise ValueError("CalibrationSpec.bond_fit_target must be a BondFitTarget.")


def _require_bootstrap_calibration_spec(calibration_spec: CalibrationSpec) -> CalibrationSpec:
    if not isinstance(calibration_spec, CalibrationSpec):
        raise ValueError("BootstrapCalibrator requires calibration_spec to be a CalibrationSpec.")
    if calibration_spec.mode is not CalibrationMode.BOOTSTRAP:
        raise ValueError("BootstrapCalibrator requires calibration_spec.mode == CalibrationMode.BOOTSTRAP.")
    if calibration_spec.regressor_names:
        raise ValueError("BootstrapCalibrator does not accept calibration_spec.regressor_names.")
    if calibration_spec.objective is not CalibrationObjective.EXACT_FIT:
        raise ValueError("BootstrapCalibrator requires calibration_spec.objective == CalibrationObjective.EXACT_FIT.")
    return calibration_spec


def _require_global_fit_calibration_spec(calibration_spec: CalibrationSpec) -> CalibrationSpec:
    if not isinstance(calibration_spec, CalibrationSpec):
        raise ValueError("GlobalFitCalibrator requires calibration_spec to be a CalibrationSpec.")
    if calibration_spec.mode is not CalibrationMode.GLOBAL_FIT:
        raise ValueError("GlobalFitCalibrator requires calibration_spec.mode == CalibrationMode.GLOBAL_FIT.")
    if calibration_spec.objective is CalibrationObjective.EXACT_FIT:
        raise ValueError("GlobalFitCalibrator does not support CalibrationObjective.EXACT_FIT.")
    if calibration_spec.objective is not CalibrationObjective.WEIGHTED_L2:
        raise ValueError("GlobalFitCalibrator requires calibration_spec.objective == CalibrationObjective.WEIGHTED_L2.")
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
    "BondFitTarget",
    "CalibrationMode",
    "CalibrationObjective",
    "CalibrationSpec",
    "CurveCalibrator",
    "GlobalFitOptimizerKind",
]
