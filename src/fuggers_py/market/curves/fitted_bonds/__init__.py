"""Cross-sectional fitted bond curves and fair-value helpers.

This subpackage exposes the fitted-bond research workflow: build an
explanatory curve directly from bond quotes, attach additive regression
adjustments, and translate the result back into dirty and clean price fair
values. The public API also includes benchmark selection, named regression
exposures, pricing adapters, and the curve families used by the fitter.
"""

from __future__ import annotations

from .fair_value import (
    BondFairValueRequest,
    BondFairValueResult,
    clean_price_from_curve,
    dirty_price_from_curve,
    fair_value_from_curve,
    fair_value_from_fit,
)
from .model import (
    BondCurveFitDiagnostics,
    CubicSplineZeroRateCurve,
    CubicSplineZeroRateCurveModel,
    ExponentialSplineCurveModel,
    ExponentialSplineDiscountCurve,
    FittedBondCurveFamily,
    FittedBondCurveModel,
    FittedBondCurve,
    FittedBondObjective,
)
from .notional_benchmarks import BenchmarkComponent, NotionalBenchmark, build_notional_benchmark
from .optimization import FittedBondCurveFitter
from .par_curve import FittedParYieldCurve, ParCurveSpec
from .pricing_adapters import (
    BondCurvePricingAdapter,
    NominalGovernmentBondPricingAdapter,
    TipsRealBondPricingAdapter,
)

__all__ = [
    "BenchmarkComponent",
    "BondFairValueRequest",
    "BondFairValueResult",
    "BondCurvePricingAdapter",
    "BondCurveFitDiagnostics",
    "NominalGovernmentBondPricingAdapter",
    "TipsRealBondPricingAdapter",
    "CubicSplineZeroRateCurve",
    "CubicSplineZeroRateCurveModel",
    "ExponentialSplineCurveModel",
    "ExponentialSplineDiscountCurve",
    "FittedBondCurveFamily",
    "FittedBondCurveFitter",
    "FittedBondCurveModel",
    "FittedBondCurve",
    "FittedBondObjective",
    "FittedParYieldCurve",
    "NotionalBenchmark",
    "ParCurveSpec",
    "build_notional_benchmark",
    "clean_price_from_curve",
    "dirty_price_from_curve",
    "fair_value_from_curve",
    "fair_value_from_fit",
]
