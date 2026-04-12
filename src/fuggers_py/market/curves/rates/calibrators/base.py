"""Shared internal calibrator contracts for rate-curve fitting."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from enum import Enum, auto
from typing import TYPE_CHECKING

from fuggers_py.market.quotes import AnyInstrumentQuote

from ..kernels import CurveKernel, KernelSpec
from ..spec import CurveSpec

if TYPE_CHECKING:
    from ..reports import CalibrationReport


class CalibrationObjective(Enum):
    """Objective convention for one curve calibration run."""

    EXACT_FIT = auto()
    WEIGHTED_L2 = auto()


class CurveCalibrator(ABC):
    """Internal calibrator contract for building one fitted curve kernel."""

    @abstractmethod
    def fit(
        self,
        quotes: Sequence[AnyInstrumentQuote],
        *,
        spec: CurveSpec,
        kernel_spec: KernelSpec,
    ) -> tuple[CurveKernel, CalibrationReport]:
        """Build one kernel plus one calibration report from market quotes."""


__all__ = [
    "CalibrationObjective",
    "CurveCalibrator",
]
