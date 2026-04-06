"""Curve infrastructure for market data, calibration, and wrappers.

This package exposes the public curve primitives used throughout the library:
term structures, builders, bumping helpers, calibration routines, and the
specialized rate, credit, inflation, repo, and fitted-bond adapters built on
top of them.
"""

from __future__ import annotations

from fuggers_py.reference.bonds.types import Tenor
from fuggers_py.core.types import Compounding, Currency
from fuggers_py.math import (
    CubicSpline,
    Interpolator,
    LinearInterpolator,
    LogLinearInterpolator,
    MonotoneConvex,
    NelsonSiegel,
    Svensson,
)

from .builder import CurveBuilder, CurveFamily, CurveInstrument, InstrumentType, SegmentBuilder
from .builders import DiscountCurveBuilder, ZeroCurveBuilder
from .bumping import (
    ArcBumpedCurve,
    ArcKeyRateBumpedCurve,
    ArcScenarioCurve,
    BumpedCurve,
    KeyRateBump,
    KeyRateBumpedCurve,
    ParallelBump,
    Scenario,
    ScenarioBump,
    ScenarioCurve,
    STANDARD_KEY_TENORS,
    flattener_50bp,
    key_rate_profile,
    parallel_down_50bp,
    parallel_up_50bp,
    steepener_50bp,
)
from .calibration import (
    BasisSwap,
    CalibrationInstrument,
    CalibrationInstrumentResult,
    CalibrationResult,
    Deposit,
    FitterConfig,
    Fra,
    Future,
    GlobalFitResult,
    GlobalFitter,
    InstrumentSet,
    Ois,
    ParametricModel,
    PiecewiseBootstrapper,
    SequentialBootstrapper,
    Swap,
)
from .conversion import ValueConverter
from .credit import CdsBootstrapPoint, CdsBootstrapResult, bootstrap_credit_curve
from .delegated import DelegatedCurve, DelegationFallback
from .derived import CurveTransform, DerivedCurve
from .discrete import DiscreteCurve, ExtrapolationMethod, InterpolationMethod
from .errors import *  # noqa: F403
from .errors import CurvesError
from .fitted_bonds import (
    BondFairValueRequest,
    BondFairValueResult,
    BondCurveFitDiagnostics,
    BondCurvePricingAdapter,
    CubicSplineZeroRateCurve,
    CubicSplineZeroRateCurveModel,
    ExponentialSplineCurveModel,
    ExponentialSplineDiscountCurve,
    FittedBondCurveFamily,
    FittedBondCurveFitter,
    FittedBondCurve,
    FittedBondCurveModel,
    FittedBondObjective,
    FittedParYieldCurve,
    NominalGovernmentBondPricingAdapter,
    ParCurveSpec,
    TipsRealBondPricingAdapter,
    build_notional_benchmark,
    clean_price_from_curve,
    dirty_price_from_curve,
    fair_value_from_curve,
    fair_value_from_fit,
)
from .forward import ForwardCurve
from .funding import RepoCurve
from .inflation import (
    BreakevenParCurve,
    BreakevenZeroCurve,
    InflationBootstrapPoint,
    InflationBootstrapResult,
    InflationCurve,
    InflationIndexCurve,
    bootstrap_inflation_curve,
)
from .bond_instruments import GovernmentCouponBond, GovernmentZeroCoupon, MarketConvention, day_count_factor
from .models import JumpDiffusionAdjustment, JumpDiffusionCurve, ShadowRateCurve, ShortRateModelCurve, ShortRateModelPoint
from .multicurve import CurrencyPair, MissingCurveError, MultiCurveEnvironment, MultiCurveEnvironmentBuilder, RateIndex
from .segmented import SegmentSource, SegmentedCurve
from .term_structure import TermStructure
from .value_type import ValueType, ValueTypeKind
from .wrappers import CreditCurve, CurveRef, DiscountCurve, RateCurve

Curve = TermStructure
CurveError = CurvesError
RateCurveDyn = RateCurve
ZeroCurve = RateCurve

__all__ = [
    "Compounding",
    "Currency",
    "Tenor",
    "ValueTypeKind",
    "ValueType",
    "ValueConverter",
    "Curve",
    "CurveRef",
    "CurveError",
    "TermStructure",
    "InterpolationMethod",
    "ExtrapolationMethod",
    "DiscreteCurve",
    "ForwardCurve",
    "DiscountCurve",
    "RateCurve",
    "CreditCurve",
    "RateCurveDyn",
    "ZeroCurve",
    "Interpolator",
    "LinearInterpolator",
    "LogLinearInterpolator",
    "CubicSpline",
    "MonotoneConvex",
    "NelsonSiegel",
    "Svensson",
    "DiscountCurveBuilder",
    "ZeroCurveBuilder",
    "CurveBuilder",
    "CurveFamily",
    "SegmentBuilder",
    "CurveInstrument",
    "InstrumentType",
    "CdsBootstrapPoint",
    "CdsBootstrapResult",
    "bootstrap_credit_curve",
    "RepoCurve",
    "BreakevenParCurve",
    "BreakevenZeroCurve",
    "InflationCurve",
    "InflationIndexCurve",
    "InflationBootstrapPoint",
    "InflationBootstrapResult",
    "bootstrap_inflation_curve",
    "GovernmentZeroCoupon",
    "GovernmentCouponBond",
    "MarketConvention",
    "day_count_factor",
    "CalibrationInstrument",
    "Deposit",
    "Fra",
    "Future",
    "Ois",
    "Swap",
    "BasisSwap",
    "InstrumentSet",
    "CalibrationInstrumentResult",
    "CalibrationResult",
    "SequentialBootstrapper",
    "PiecewiseBootstrapper",
    "ParametricModel",
    "FitterConfig",
    "GlobalFitResult",
    "GlobalFitter",
    "ShortRateModelCurve",
    "ShortRateModelPoint",
    "ShadowRateCurve",
    "JumpDiffusionAdjustment",
    "JumpDiffusionCurve",
    "ParallelBump",
    "KeyRateBump",
    "Scenario",
    "ScenarioBump",
    "BumpedCurve",
    "KeyRateBumpedCurve",
    "ScenarioCurve",
    "ArcBumpedCurve",
    "ArcKeyRateBumpedCurve",
    "ArcScenarioCurve",
    "STANDARD_KEY_TENORS",
    "key_rate_profile",
    "parallel_up_50bp",
    "parallel_down_50bp",
    "steepener_50bp",
    "flattener_50bp",
    "CurveTransform",
    "DelegationFallback",
    "DelegatedCurve",
    "DerivedCurve",
    "SegmentSource",
    "SegmentedCurve",
    "CurrencyPair",
    "RateIndex",
    "MultiCurveEnvironment",
    "MultiCurveEnvironmentBuilder",
    "MissingCurveError",
    "BondFairValueRequest",
    "BondFairValueResult",
    "BondCurveFitDiagnostics",
    "BondCurvePricingAdapter",
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
    "NominalGovernmentBondPricingAdapter",
    "ParCurveSpec",
    "TipsRealBondPricingAdapter",
    "build_notional_benchmark",
    "clean_price_from_curve",
    "dirty_price_from_curve",
    "fair_value_from_curve",
    "fair_value_from_fit",
]
