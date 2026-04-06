"""Calibration helpers for :mod:`fuggers_py.market.curves`.

This package exposes curve-calibration instruments, sequential and piecewise
bootstrappers, and the global parametric fit entry points. Calibration
instruments quote raw decimal rates except for futures, which use price-level
quotes.
"""

from __future__ import annotations

from .global_fit import FitterConfig, GlobalFitResult, GlobalFitter, ParametricModel
from .instruments import BasisSwap, CalibrationInstrument, Deposit, Fra, Future, InstrumentSet, Ois, Swap
from .piecewise import PiecewiseBootstrapper
from .sequential import CalibrationInstrumentResult, CalibrationResult, SequentialBootstrapper

__all__ = [
    "Deposit",
    "Fra",
    "Future",
    "Ois",
    "Swap",
    "BasisSwap",
    "CalibrationInstrument",
    "InstrumentSet",
    "CalibrationInstrumentResult",
    "CalibrationResult",
    "SequentialBootstrapper",
    "PiecewiseBootstrapper",
    "ParametricModel",
    "FitterConfig",
    "GlobalFitResult",
    "GlobalFitter",
]
