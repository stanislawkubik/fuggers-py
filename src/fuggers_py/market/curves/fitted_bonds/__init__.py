"""Cross-sectional fitted bond curves and fair-value helpers.

This subpackage exposes the fitted-bond research workflow: build an
explanatory curve directly from bond quotes, attach additive regression
adjustments, and translate the result back into dirty and clean price fair
values. The public API also includes benchmark selection, named regression
exposures, pricing adapters, and the curve families used by the fitter.
"""

from __future__ import annotations

from .bond_curve import BondCurve
from .fair_value import (
    BondFairValueRequest,
    BondFairValueResult,
    clean_price_from_curve,
    dirty_price_from_curve,
    fair_value_from_curve,
    fair_value_from_fit,
)
from .model import (
    BondCurveDiagnostics,
    BondCurvePoint,
    CubicSplineZeroRateCurve,
    CubicSplineZeroRateCurveModel,
    ExponentialSplineCurveModel,
    ExponentialSplineZeroRateCurve,
    FittedBondCurveFamily,
)
from .notional_benchmarks import BenchmarkComponent, NotionalBenchmark, build_notional_benchmark
from .optimization import BondCurveFitter
from .par_curve import FittedParYieldCurve, ParCurveSpec
from .pricing_adapters import (
    BondCurvePricingAdapter,
    NominalGovernmentBondPricingAdapter,
    TipsRealBondPricingAdapter,
)

__all__ = [
    "BenchmarkComponent",
    "BondCurve",
    "BondFairValueRequest",
    "BondFairValueResult",
    "BondCurveDiagnostics",
    "BondCurvePoint",
    "BondCurvePricingAdapter",
    "NominalGovernmentBondPricingAdapter",
    "TipsRealBondPricingAdapter",
    "CubicSplineZeroRateCurve",
    "CubicSplineZeroRateCurveModel",
    "ExponentialSplineCurveModel",
    "ExponentialSplineZeroRateCurve",
    "FittedBondCurveFamily",
    "BondCurveFitter",
    "FittedParYieldCurve",
    "NotionalBenchmark",
    "ParCurveSpec",
    "build_notional_benchmark",
    "clean_price_from_curve",
    "dirty_price_from_curve",
    "fair_value_from_curve",
    "fair_value_from_fit",
]
