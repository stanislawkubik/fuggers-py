"""Explicit ASW / basis / adjusted-CDS link decomposition.

The common-currency floating spread is the sum of the asset-swap spread, same-
currency basis, and cross-currency basis. Any adjusted CDS input is compared to
that total using the residual sign `floating spread - adjusted CDS`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ._shared import to_decimal
from .basis_swapped_bonds import CommonCurrencyFloatingBondView


@dataclass(frozen=True, slots=True)
class AswBasisCdsLinkBreakdown:
    """Breakdown linking asset-swap, basis, and adjusted-CDS spreads."""

    asset_swap_spread: Decimal
    same_currency_basis: Decimal
    cross_currency_basis: Decimal
    funding_basis_total: Decimal
    common_currency_floating_spread: Decimal
    adjusted_cds_spread: Decimal | None = None
    residual_to_adjusted_cds: Decimal | None = None


def decompose_asw_basis_cds_links(
    *,
    asset_swap_spread: object,
    same_currency_basis: object = Decimal(0),
    cross_currency_basis: object = Decimal(0),
    adjusted_cds_spread: object | None = None,
) -> AswBasisCdsLinkBreakdown:
    """Return the raw decimal ASW / basis / CDS link decomposition."""
    asset_swap_value = to_decimal(asset_swap_spread)
    same_currency_value = to_decimal(same_currency_basis)
    cross_currency_value = to_decimal(cross_currency_basis)
    common_currency_floating_spread = asset_swap_value + same_currency_value + cross_currency_value
    adjusted_cds_value = None if adjusted_cds_spread is None else to_decimal(adjusted_cds_spread)
    return AswBasisCdsLinkBreakdown(
        asset_swap_spread=asset_swap_value,
        same_currency_basis=same_currency_value,
        cross_currency_basis=cross_currency_value,
        funding_basis_total=same_currency_value + cross_currency_value,
        common_currency_floating_spread=common_currency_floating_spread,
        adjusted_cds_spread=adjusted_cds_value,
        residual_to_adjusted_cds=None
        if adjusted_cds_value is None
        else common_currency_floating_spread - adjusted_cds_value,
    )


def decompose_floating_view_links(
    floating_view: CommonCurrencyFloatingBondView,
    *,
    adjusted_cds_spread: object | None = None,
) -> AswBasisCdsLinkBreakdown:
    """Decompose a floating common-currency view against an adjusted CDS."""
    return decompose_asw_basis_cds_links(
        asset_swap_spread=floating_view.asset_swap_spread,
        same_currency_basis=floating_view.same_currency_basis,
        cross_currency_basis=floating_view.cross_currency_basis,
        adjusted_cds_spread=adjusted_cds_spread,
    )


__all__ = [
    "AswBasisCdsLinkBreakdown",
    "decompose_asw_basis_cds_links",
    "decompose_floating_view_links",
]
