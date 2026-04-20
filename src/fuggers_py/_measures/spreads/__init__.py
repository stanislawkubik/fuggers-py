"""Compatibility wrapper for the new first-layer bond spread facade."""

from __future__ import annotations

__all__ = [
    "SecurityId",
    "BenchmarkSpec",
    "BenchmarkKind",
    "Sovereign",
    "SupranationalIssuer",
    "GovernmentBenchmark",
    "GovernmentCurve",
    "GSpreadCalculator",
    "GQDSecuredUnsecuredBasisModel",
    "ISpreadCalculator",
    "ZSpreadCalculator",
    "ReferenceRateBreakdown",
    "reference_rate_decomposition",
    "SecuredUnsecuredBasisModel",
    "secured_unsecured_overnight_basis",
    "CompoundingConvexityBreakdown",
    "simple_to_compounded_equivalent_rate",
    "compounding_convexity_breakdown",
    "adjusted_term_rate",
    "g_spread",
    "g_spread_bps",
    "g_spread_with_benchmark",
    "g_spread_with_benchmark_bps",
    "i_spread",
    "i_spread_bps",
    "z_spread",
    "z_spread_from_curve",
    "DiscountMarginCalculator",
    "simple_margin",
    "z_discount_margin",
    "OASCalculator",
    "ASWType",
    "BaseSpreadAdjustment",
    "BalanceSheetSpreadOverlay",
    "CapitalAdjustmentBreakdown",
    "CapitalSpreadAdjustment",
    "FundingSpreadOverlayResult",
    "HaircutAdjustmentBreakdown",
    "HaircutSpreadAdjustment",
    "ParParAssetSwap",
    "ProceedsAssetSwap",
    "ShadowCostAdjustmentBreakdown",
    "ShadowCostSpreadAdjustment",
    "SpreadAdjustment",
    "SpreadAdjustmentBreakdown",
    "SpreadAdjustmentSummary",
    "apply_balance_sheet_overlays",
    "apply_funding_spread_overlays",
    "capital_adjustment_breakdown",
    "capital_spread_adjustment",
    "compose_spread_adjustments",
    "haircut_adjustment_breakdown",
    "haircut_spread_adjustment",
    "shadow_cost_adjustment_breakdown",
    "shadow_cost_spread_adjustment",
    "utilization_ratio",
]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import fuggers_py.bonds.spreads as _public_module

    return getattr(_public_module, name)


def __dir__() -> list[str]:
    return sorted(__all__)
