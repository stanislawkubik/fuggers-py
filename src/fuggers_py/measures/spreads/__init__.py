"""Spread analytics for the analytics layer.

Unsuffixed yields, rates, and spreads use raw decimal units across the public
analytics surface. Use explicit ``*_bps`` helpers when a display/reporting
workflow needs basis-point formatting.
"""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py.reference.bonds.types import ASWType, Cusip, Figi, Isin, Sedol

from .adjustments import (
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
from .asw import ParParAssetSwap, ProceedsAssetSwap
from .benchmark import BenchmarkKind, BenchmarkSpec
from .compounding_convexity import (
    CompoundingConvexityBreakdown,
    adjusted_term_rate,
    compounding_convexity_breakdown,
    simple_to_compounded_equivalent_rate,
)
from .discount_margin import DiscountMarginCalculator, simple_margin, z_discount_margin
from .government_curve import GovernmentBenchmark, GovernmentCurve
from .gspread import GSpreadCalculator, g_spread, g_spread_bps, g_spread_with_benchmark, g_spread_with_benchmark_bps
from .ispread import ISpreadCalculator, i_spread, i_spread_bps
from .oas import OASCalculator
from .reference_rates import ReferenceRateBreakdown, reference_rate_decomposition
from .secured_unsecured_basis import (
    GQDSecuredUnsecuredBasisModel,
    SecuredUnsecuredBasisModel,
    secured_unsecured_overnight_basis,
)
from .sovereign import Sovereign, SupranationalIssuer
from .zspread import ZSpreadCalculator, z_spread, z_spread_from_curve


@dataclass(frozen=True, slots=True)
class SecurityId:
    """Typed security identifier used by spread analytics.

    Parameters
    ----------
    identifier_type
        Identifier family label such as ``CUSIP`` or ``ISIN``.
    value
        Normalized identifier value.
    """

    identifier_type: str
    value: str

    @classmethod
    def cusip(cls, value: str) -> "SecurityId":
        """Build a normalized CUSIP identifier."""
        return cls("CUSIP", Cusip.new(value).value)

    @classmethod
    def cusip_unchecked(cls, value: str) -> "SecurityId":
        """Build a CUSIP identifier without validation."""
        return cls("CUSIP", value.strip().upper())

    @classmethod
    def isin(cls, value: str) -> "SecurityId":
        """Build a normalized ISIN identifier."""
        return cls("ISIN", Isin.new(value).value)

    @classmethod
    def sedol(cls, value: str) -> "SecurityId":
        """Build a normalized SEDOL identifier."""
        return cls("SEDOL", Sedol.new(value).value)

    @classmethod
    def figi(cls, value: str) -> "SecurityId":
        """Build a normalized FIGI identifier."""
        return cls("FIGI", Figi.new(value).value)

    def id_type(self) -> str:
        """Return the identifier family label."""
        return self.identifier_type

    def as_str(self) -> str:
        """Return the normalized identifier value."""
        return self.value

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.identifier_type}:{self.value}"


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
