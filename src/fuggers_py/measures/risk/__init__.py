"""Risk analytics (`fuggers_py.measures.risk`).

This package exposes duration, convexity, DV01, hedging, and VaR helpers.
Duration, convexity, and DV01 outputs are documented as positive-magnitude
analytics values unless a helper explicitly states otherwise. VaR helpers
return non-negative loss magnitudes, and hedge helpers return scaling ratios
or direction metadata rather than executable trade instructions.
"""

from __future__ import annotations

from .calculator import BondRiskCalculator, BondRiskMetrics, EffectiveDurationCalculator
from .convexity import Convexity, analytical_convexity, effective_convexity, price_change_with_convexity
from .duration import (
    DEFAULT_BUMP_SIZE,
    SMALL_BUMP_SIZE,
    STANDARD_KEY_RATE_TENORS,
    Duration,
    KeyRateDuration,
    KeyRateDurationCalculator,
    KeyRateDurations,
    effective_duration,
    key_rate_duration_at_tenor,
    macaulay_duration,
    modified_duration,
    modified_from_macaulay,
    spread_duration,
)
from .dv01 import DV01, dv01_from_duration, dv01_from_prices, dv01_per_100_face, notional_from_dv01
from .hedging import (
    HedgeDirection,
    HedgeRecommendation,
    PortfolioRisk,
    Position,
    aggregate_portfolio_risk,
    duration_hedge_ratio,
    dv01_hedge_ratio,
)
from .var import VaRMethod, VaRResult, historical_var, parametric_var, parametric_var_from_dv01

DurationType = Duration

__all__ = [
    "BondRiskCalculator",
    "BondRiskMetrics",
    "EffectiveDurationCalculator",
    # Duration
    "Duration",
    "DurationType",
    "macaulay_duration",
    "modified_duration",
    "modified_from_macaulay",
    "effective_duration",
    "spread_duration",
    "key_rate_duration_at_tenor",
    "KeyRateDuration",
    "KeyRateDurations",
    "KeyRateDurationCalculator",
    "DEFAULT_BUMP_SIZE",
    "SMALL_BUMP_SIZE",
    "STANDARD_KEY_RATE_TENORS",
    # Convexity
    "Convexity",
    "analytical_convexity",
    "effective_convexity",
    "price_change_with_convexity",
    # DV01
    "DV01",
    "dv01_from_duration",
    "dv01_from_prices",
    "dv01_per_100_face",
    "notional_from_dv01",
    # Hedging
    "duration_hedge_ratio",
    "dv01_hedge_ratio",
    "aggregate_portfolio_risk",
    "HedgeDirection",
    "HedgeRecommendation",
    "PortfolioRisk",
    "Position",
    # VaR
    "historical_var",
    "parametric_var",
    "parametric_var_from_dv01",
    "VaRMethod",
    "VaRResult",
]
