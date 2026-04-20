"""Compatibility wrapper for the new first-layer bond risk facade."""

from __future__ import annotations

__all__ = [
    "BondRiskCalculator",
    "BondRiskMetrics",
    "EffectiveDurationCalculator",
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
    "Convexity",
    "analytical_convexity",
    "effective_convexity",
    "price_change_with_convexity",
    "DV01",
    "dv01_from_duration",
    "dv01_from_prices",
    "dv01_per_100_face",
    "notional_from_dv01",
    "duration_hedge_ratio",
    "dv01_hedge_ratio",
    "aggregate_portfolio_risk",
    "HedgeDirection",
    "HedgeRecommendation",
    "PortfolioRisk",
    "Position",
    "historical_var",
    "parametric_var",
    "parametric_var_from_dv01",
    "VaRMethod",
    "VaRResult",
]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import fuggers_py.bonds.risk as _public_module

    return getattr(_public_module, name)


def __dir__() -> list[str]:
    return sorted(__all__)
