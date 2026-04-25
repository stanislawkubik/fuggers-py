"""Full asset-swap pricing helpers.

Quoted asset-swap spreads are raw decimals, and bond prices are handled in
percent of par. The pricer decomposes the quoted spread into funding and
credit components using the resolved curve set.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.bonds.spreads import ParParAssetSwap, ProceedsAssetSwap, ReferenceRateBreakdown, reference_rate_decomposition
from fuggers_py.bonds.types import ASWType

from ._curve_resolver import resolve_discount_curve, resolve_projection_curve
from .asset_swap import AssetSwap


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class AssetSwapBreakdown:
    """Detailed asset-swap decomposition.

    Attributes
    ----------
    market_clean_price, market_dirty_price:
        Bond market prices in percent of par.
    accrued_interest:
        Accrued interest in currency units.
    quoted_spread:
        Asset-swap spread as a raw decimal.
    normalized_annuity:
        Discounted fixed-leg annuity used to convert spread to PV.
    spread_pv_factor:
        Currency PV per unit spread.
    effective_floating_notional:
        Floating-leg notional after any proceeds-style scaling.
    reference_rates:
        Funding decomposition from the analytics spread helper.
    funding_component_pv, credit_component_pv:
        PV contributions of the funding and credit components.
    """

    market_clean_price: Decimal
    market_dirty_price: Decimal
    accrued_interest: Decimal
    quoted_spread: Decimal
    normalized_annuity: Decimal
    spread_pv_factor: Decimal
    effective_floating_notional: Decimal
    reference_rates: ReferenceRateBreakdown
    funding_component_pv: Decimal
    credit_component_pv: Decimal


@dataclass(frozen=True, slots=True)
class AssetSwapPricingResult:
    """Asset-swap pricing output.

    Attributes
    ----------
    par_spread:
        Par asset-swap spread as a raw decimal.
    present_value:
        Present value in the asset-swap currency.
    funding_component:
        Funding spread component as a raw decimal.
    credit_component:
        Credit spread component as a raw decimal.
    breakdown:
        Detailed breakdown of the price decomposition.
    """

    par_spread: Decimal
    present_value: Decimal
    funding_component: Decimal
    credit_component: Decimal
    breakdown: AssetSwapBreakdown


@dataclass(frozen=True, slots=True)
class AssetSwapPricer:
    """Price asset swaps against the resolved curve set.

    The pricer decomposes the asset-swap spread into par, funding, and credit
    components using the resolved projection and discount curves.
    """

    def _calculator(self, curve: object, asset_swap_type: ASWType) -> ParParAssetSwap | ProceedsAssetSwap:
        if asset_swap_type is ASWType.PROCEEDS:
            return ProceedsAssetSwap(curve)
        return ParParAssetSwap(curve)

    def _term_curve(self, asset_swap: AssetSwap, curves: object):
        return resolve_projection_curve(
            curves,
            currency=asset_swap.currency(),
            index_name=asset_swap.floating_leg.index_name,
            index_tenor=asset_swap.floating_leg.index_tenor,
        )

    def _rate_from_curve(self, curve: object, asset_swap: AssetSwap) -> Decimal:
        return self._calculator(curve, asset_swap.asset_swap_type)._swap_rate(  # noqa: SLF001
            asset_swap.bond,
            asset_swap.settlement_date,
        )

    def _resolved_reference_rates(self, asset_swap: AssetSwap, curves: object) -> ReferenceRateBreakdown:
        term_curve = self._term_curve(asset_swap, curves)
        discount_curve = resolve_discount_curve(curves, asset_swap.currency())
        repo_curve = curves.repo_curve or curves.collateral_curve or discount_curve
        gc_curve = curves.collateral_curve or discount_curve
        unsecured_curve = curves.forward_curve or discount_curve

        repo_rate = asset_swap.repo_rate or self._rate_from_curve(repo_curve, asset_swap)
        gc_rate = asset_swap.general_collateral_rate or self._rate_from_curve(gc_curve, asset_swap)
        unsecured_overnight_rate = asset_swap.unsecured_overnight_rate or self._rate_from_curve(unsecured_curve, asset_swap)
        term_rate = asset_swap.term_rate or self._rate_from_curve(term_curve, asset_swap)
        return reference_rate_decomposition(
            repo_rate=repo_rate,
            general_collateral_rate=gc_rate,
            unsecured_overnight_rate=unsecured_overnight_rate,
            term_rate=term_rate,
            convexity_adjustment=asset_swap.compounding_convexity_adjustment,
        )

    def par_spread(self, asset_swap: AssetSwap, curves: object) -> Decimal:
        """Return the par asset-swap spread as a raw decimal.

        The spread is the quoted fixed/floating spread that would zero the
        asset-swap PV under the resolved curves.
        """

        term_curve = self._term_curve(asset_swap, curves)
        return self._calculator(term_curve, asset_swap.asset_swap_type).calculate(
            asset_swap.bond,
            asset_swap.dirty_price(),
            asset_swap.settlement_date,
        )

    def funding_component(self, asset_swap: AssetSwap, curves: object) -> Decimal:
        """Return the funding component of the par spread."""

        return self._resolved_reference_rates(asset_swap, curves).total_funding_basis

    def credit_component(self, asset_swap: AssetSwap, curves: object) -> Decimal:
        """Return the credit component of the par spread."""

        return self.par_spread(asset_swap, curves) - self.funding_component(asset_swap, curves)

    def pv(self, asset_swap: AssetSwap, curves: object) -> Decimal:
        """Return the asset-swap present value."""

        result = self.price(asset_swap, curves)
        return result.present_value

    def price(self, asset_swap: AssetSwap, curves: object) -> AssetSwapPricingResult:
        """Return the full asset-swap pricing result.

        The result includes the par spread, PV, funding and credit spread
        components, and a detailed breakdown of the pricing inputs.
        """

        term_curve = self._term_curve(asset_swap, curves)
        calculator = self._calculator(term_curve, asset_swap.asset_swap_type)
        par_spread = calculator.calculate(
            asset_swap.bond,
            asset_swap.dirty_price(),
            asset_swap.settlement_date,
        )
        normalized_annuity = calculator._annuity(asset_swap.bond, asset_swap.settlement_date)  # noqa: SLF001
        spread_pv_factor = normalized_annuity * asset_swap.effective_floating_notional() / Decimal(100)
        sign = asset_swap.floating_leg.pay_receive.sign()

        reference_rates = self._resolved_reference_rates(asset_swap, curves)
        funding_component = reference_rates.total_funding_basis
        credit_component = par_spread - funding_component
        present_value = sign * spread_pv_factor * (par_spread - asset_swap.quoted_spread)
        breakdown = AssetSwapBreakdown(
            market_clean_price=asset_swap.clean_price(),
            market_dirty_price=asset_swap.dirty_price(),
            accrued_interest=asset_swap.accrued_interest(),
            quoted_spread=asset_swap.quoted_spread,
            normalized_annuity=normalized_annuity,
            spread_pv_factor=spread_pv_factor,
            effective_floating_notional=asset_swap.effective_floating_notional(),
            reference_rates=reference_rates,
            funding_component_pv=sign * spread_pv_factor * funding_component,
            credit_component_pv=sign * spread_pv_factor * credit_component,
        )
        return AssetSwapPricingResult(
            par_spread=par_spread,
            present_value=present_value,
            funding_component=funding_component,
            credit_component=credit_component,
            breakdown=breakdown,
        )


__all__ = [
    "AssetSwapBreakdown",
    "AssetSwapPricer",
    "AssetSwapPricingResult",
]
