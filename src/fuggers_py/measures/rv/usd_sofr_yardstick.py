"""USD SOFR yardstick comparisons for global bond RV.

The residuals are raw decimal spreads.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .asw_basis_cds_links import AswBasisCdsLinkBreakdown


@dataclass(frozen=True, slots=True)
class UsdSofrAdjustedRvMeasure:
    """USD SOFR spread compared with a yardstick and optional adjusted CDS."""

    usd_sofr_spread: Decimal
    yardstick_spread: Decimal
    adjusted_cds_spread: Decimal | None
    residual_to_yardstick: Decimal
    residual_to_adjusted_cds: Decimal | None

def usd_sofr_adjusted_rv_from_links(
    link_breakdown: "AswBasisCdsLinkBreakdown",
    *,
    yardstick_spread: object,
) -> UsdSofrAdjustedRvMeasure:
    """Build a USD SOFR RV measure from an explicit link breakdown."""
    yardstick_value = yardstick_spread if isinstance(yardstick_spread, Decimal) else Decimal(str(yardstick_spread))
    return UsdSofrAdjustedRvMeasure(
        usd_sofr_spread=link_breakdown.common_currency_floating_spread,
        yardstick_spread=yardstick_value,
        adjusted_cds_spread=link_breakdown.adjusted_cds_spread,
        residual_to_yardstick=link_breakdown.common_currency_floating_spread - yardstick_value,
        residual_to_adjusted_cds=link_breakdown.residual_to_adjusted_cds,
    )


__all__ = [
    "UsdSofrAdjustedRvMeasure",
    "usd_sofr_adjusted_rv_from_links",
]
