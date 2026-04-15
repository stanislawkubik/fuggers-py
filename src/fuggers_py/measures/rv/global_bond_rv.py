"""Global bond RV workflows built on basis-swapped bond views."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .asw_basis_cds_links import decompose_asw_basis_cds_links
from .basis_swapped_bonds import (
    CommonCurrencyFloatingBondView,
    bond_to_common_currency_floating,
)
from .usd_sofr_yardstick import UsdSofrAdjustedRvMeasure, usd_sofr_adjusted_rv_from_links

@dataclass(frozen=True, slots=True)
class GlobalUsdSofrRvResult:
    """Relative-value result for a USD SOFR common-currency floating view."""

    usd_sofr_measure: UsdSofrAdjustedRvMeasure
    residual_bps: Decimal
    classification: str
    floating_view: CommonCurrencyFloatingBondView

def global_usd_sofr_rv(
    asset_swap,
    curves,
    *,
    yardstick_spread: object,
    adjusted_cds_spread: object | None = None,
    local_basis_swap=None,
    cross_currency_basis_swap=None,
    threshold_bps: object = Decimal(0),
) -> GlobalUsdSofrRvResult:
    """Compare a USD SOFR floating view against a deterministic yardstick."""
    floating_view = bond_to_common_currency_floating(
        asset_swap,
        curves,
        local_basis_swap=local_basis_swap,
        cross_currency_basis_swap=cross_currency_basis_swap,
    )
    if floating_view.target_currency.code() != "USD" or floating_view.target_index_name != "SOFR":
        raise ValueError("global_usd_sofr_rv requires a USD SOFR common-currency floating view.")
    measure = usd_sofr_adjusted_rv_from_links(
        decompose_asw_basis_cds_links(
            asset_swap_spread=floating_view.asset_swap_spread,
            same_currency_basis=floating_view.same_currency_basis,
            cross_currency_basis=floating_view.cross_currency_basis,
            adjusted_cds_spread=adjusted_cds_spread,
        ),
        yardstick_spread=yardstick_spread,
    )
    residual_bps = measure.residual_to_yardstick * Decimal("10000")
    threshold_value = threshold_bps if isinstance(threshold_bps, Decimal) else Decimal(str(threshold_bps))
    return GlobalUsdSofrRvResult(
        usd_sofr_measure=measure,
        residual_bps=residual_bps,
        classification="CHEAP"
        if residual_bps > threshold_value
        else "RICH" if residual_bps < -threshold_value else "NEUTRAL",
        floating_view=floating_view,
    )


__all__ = [
    "GlobalUsdSofrRvResult",
    "global_usd_sofr_rv",
]
