"""Bond spread analytics for the first-layer public facade."""

from __future__ import annotations

from dataclasses import dataclass

from ._spreads.adjustments import (
    BaseSpreadAdjustment,
    BalanceSheetSpreadOverlay,
    CapitalAdjustmentBreakdown,
    CapitalSpreadAdjustment,
    FundingSpreadOverlayResult,
    HaircutAdjustmentBreakdown,
    HaircutSpreadAdjustment,
    ShadowCostAdjustmentBreakdown,
    ShadowCostSpreadAdjustment,
    SpreadAdjustment,
    SpreadAdjustmentBreakdown,
    SpreadAdjustmentSummary,
    apply_balance_sheet_overlays,
    apply_funding_spread_overlays,
    capital_adjustment_breakdown,
    capital_spread_adjustment,
    compose_spread_adjustments,
    haircut_adjustment_breakdown,
    haircut_spread_adjustment,
    shadow_cost_adjustment_breakdown,
    shadow_cost_spread_adjustment,
    utilization_ratio,
)
from ._spreads.asw import ParParAssetSwap, ProceedsAssetSwap
from ._spreads.benchmark import BenchmarkKind, BenchmarkSpec
from ._spreads.compounding_convexity import (
    CompoundingConvexityBreakdown,
    adjusted_term_rate,
    compounding_convexity_breakdown,
    simple_to_compounded_equivalent_rate,
)
from ._spreads.discount_margin import DiscountMarginCalculator, simple_margin, z_discount_margin
from ._spreads.government_curve import GovernmentBenchmark, GovernmentCurve
from ._spreads.gspread import (
    GSpreadCalculator,
    g_spread,
    g_spread_bps,
    g_spread_with_benchmark,
    g_spread_with_benchmark_bps,
)
from ._spreads.ispread import ISpreadCalculator, i_spread, i_spread_bps
from ._spreads.oas import OASCalculator
from ._spreads.reference_rates import ReferenceRateBreakdown, reference_rate_decomposition
from ._spreads.secured_unsecured_basis import (
    GQDSecuredUnsecuredBasisModel,
    SecuredUnsecuredBasisModel,
    secured_unsecured_overnight_basis,
)
from ._spreads.sovereign import Sovereign, SupranationalIssuer
from ._spreads.zspread import ZSpreadCalculator, z_spread, z_spread_from_curve
from .types import ASWType, Cusip, Figi, Isin, Sedol


@dataclass(frozen=True, slots=True)
class SecurityId:
    """Typed security identifier used by bond spread analytics."""

    identifier_type: str
    value: str

    @classmethod
    def cusip(cls, value: str) -> "SecurityId":
        return cls("CUSIP", Cusip.new(value).value)

    @classmethod
    def cusip_unchecked(cls, value: str) -> "SecurityId":
        return cls("CUSIP", value.strip().upper())

    @classmethod
    def isin(cls, value: str) -> "SecurityId":
        return cls("ISIN", Isin.new(value).value)

    @classmethod
    def sedol(cls, value: str) -> "SecurityId":
        return cls("SEDOL", Sedol.new(value).value)

    @classmethod
    def figi(cls, value: str) -> "SecurityId":
        return cls("FIGI", Figi.new(value).value)

    def id_type(self) -> str:
        return self.identifier_type

    def as_str(self) -> str:
        return self.value

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.identifier_type}:{self.value}"


__all__ = [
    "ASWType",
    "BaseSpreadAdjustment",
    "BalanceSheetSpreadOverlay",
    "BenchmarkKind",
    "BenchmarkSpec",
    "CapitalAdjustmentBreakdown",
    "CapitalSpreadAdjustment",
    "CompoundingConvexityBreakdown",
    "DiscountMarginCalculator",
    "FundingSpreadOverlayResult",
    "GQDSecuredUnsecuredBasisModel",
    "GSpreadCalculator",
    "GovernmentBenchmark",
    "GovernmentCurve",
    "HaircutAdjustmentBreakdown",
    "HaircutSpreadAdjustment",
    "ISpreadCalculator",
    "OASCalculator",
    "ParParAssetSwap",
    "ProceedsAssetSwap",
    "ReferenceRateBreakdown",
    "SecuredUnsecuredBasisModel",
    "SecurityId",
    "ShadowCostAdjustmentBreakdown",
    "ShadowCostSpreadAdjustment",
    "Sovereign",
    "SpreadAdjustment",
    "SpreadAdjustmentBreakdown",
    "SpreadAdjustmentSummary",
    "SupranationalIssuer",
    "ZSpreadCalculator",
    "adjusted_term_rate",
    "apply_balance_sheet_overlays",
    "apply_funding_spread_overlays",
    "capital_adjustment_breakdown",
    "capital_spread_adjustment",
    "compounding_convexity_breakdown",
    "compose_spread_adjustments",
    "g_spread",
    "g_spread_bps",
    "g_spread_with_benchmark",
    "g_spread_with_benchmark_bps",
    "haircut_adjustment_breakdown",
    "haircut_spread_adjustment",
    "i_spread",
    "i_spread_bps",
    "reference_rate_decomposition",
    "secured_unsecured_overnight_basis",
    "shadow_cost_adjustment_breakdown",
    "shadow_cost_spread_adjustment",
    "simple_margin",
    "simple_to_compounded_equivalent_rate",
    "utilization_ratio",
    "z_discount_margin",
    "z_spread",
    "z_spread_from_curve",
]
