"""USD SOFR yardstick comparisons for global bond RV.

The residuals are raw decimal spreads. The helper that accepts a floating view
requires the common-currency view to be explicitly USD SOFR.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .asw_basis_cds_links import AswBasisCdsLinkBreakdown, decompose_floating_view_links
from .basis_swapped_bonds import CommonCurrencyFloatingBondView


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class UsdSofrAdjustedRvMeasure:
    """USD SOFR spread compared with a yardstick and optional adjusted CDS."""

    usd_sofr_spread: Decimal
    yardstick_spread: Decimal
    adjusted_cds_spread: Decimal | None
    residual_to_yardstick: Decimal
    residual_to_adjusted_cds: Decimal | None


def usd_sofr_adjusted_rv_measure(
    floating_view: CommonCurrencyFloatingBondView,
    *,
    yardstick_spread: object,
    adjusted_cds_spread: object | None = None,
) -> UsdSofrAdjustedRvMeasure:
    """Build a USD SOFR RV measure from a common-currency floating view."""
    if floating_view.target_currency.code() != "USD" or floating_view.target_index_name != "SOFR":
        raise ValueError("usd_sofr_adjusted_rv_measure requires a USD SOFR common-currency floating view.")
    link_breakdown = decompose_floating_view_links(
        floating_view,
        adjusted_cds_spread=adjusted_cds_spread,
    )
    return usd_sofr_adjusted_rv_from_links(
        link_breakdown,
        yardstick_spread=yardstick_spread,
    )


def usd_sofr_adjusted_rv_from_links(
    link_breakdown: AswBasisCdsLinkBreakdown,
    *,
    yardstick_spread: object,
) -> UsdSofrAdjustedRvMeasure:
    """Build a USD SOFR RV measure from an explicit link breakdown."""
    yardstick_value = _to_decimal(yardstick_spread)
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
    "usd_sofr_adjusted_rv_measure",
]
