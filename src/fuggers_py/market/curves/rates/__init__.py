"""Rates-specific public surface for market curves.

The root ``market.curves`` package stays intentionally small. This
``rates`` package re-exports the public construction and report vocabulary
needed to build and inspect ``YieldCurve`` objects without reaching into
internal submodules.
"""

from .base import DiscountingCurve, RatesTermStructure, RelativeRateCurve, YieldCurve
from .calibrators import BondFitTarget, CalibrationMode, CalibrationObjective, CalibrationSpec, GlobalFitOptimizerKind
from .enums import CurveType, ExtrapolationPolicy, RateSpace
from .kernels.base import CurveKernel, CurveKernelKind, KernelSpec
from .reports import CalibrationPoint, CalibrationReport, GlobalFitPoint, GlobalFitReport
from .spec import CurveSpec

__all__ = [
    "BondFitTarget",
    "CalibrationMode",
    "CalibrationObjective",
    "CalibrationPoint",
    "CalibrationReport",
    "CurveSpec",
    "CurveKernel",
    "CurveKernelKind",
    "CurveType",
    "CalibrationSpec",
    "DiscountingCurve",
    "ExtrapolationPolicy",
    "GlobalFitPoint",
    "GlobalFitOptimizerKind",
    "GlobalFitReport",
    "KernelSpec",
    "RateSpace",
    "RatesTermStructure",
    "RelativeRateCurve",
    "YieldCurve",
]
