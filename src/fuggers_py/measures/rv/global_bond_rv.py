"""Global bond RV workflows built on basis-swapped bond views.

The floating view chains asset-swap, same-currency basis, and FX-adjusted basis
spreads additively. The fixed view then adds the target-currency par swap rate.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.market.curves.fitted_bonds import FittedBondCurve

from .basis_swapped_bonds import (
    CommonCurrencyFixedBondView,
    CommonCurrencyFloatingBondView,
    bond_to_common_currency_fixed,
    bond_to_common_currency_floating,
)
from .constant_maturity import generate_constant_maturity_benchmark
from .usd_sofr_yardstick import UsdSofrAdjustedRvMeasure, usd_sofr_adjusted_rv_measure


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _classification(residual_bps: Decimal, threshold_bps: Decimal) -> str:
    if residual_bps > threshold_bps:
        return "CHEAP"
    if residual_bps < -threshold_bps:
        return "RICH"
    return "NEUTRAL"


@dataclass(frozen=True, slots=True)
class GlobalFixedCashflowRvResult:
    """Relative-value result for a fixed-cashflow common-currency view."""

    common_currency_fixed_rate: Decimal
    fitted_curve_yardstick: Decimal
    residual: Decimal
    residual_bps: Decimal
    classification: str
    fixed_view: CommonCurrencyFixedBondView


@dataclass(frozen=True, slots=True)
class GlobalUsdSofrRvResult:
    """Relative-value result for a USD SOFR common-currency floating view."""

    usd_sofr_measure: UsdSofrAdjustedRvMeasure
    residual_bps: Decimal
    classification: str
    floating_view: CommonCurrencyFloatingBondView


def global_fixed_cashflow_rv(
    asset_swap,
    curves,
    fit_result: FittedBondCurve,
    *,
    local_basis_swap=None,
    cross_currency_basis_swap=None,
    threshold_bps: object = Decimal(0),
    fixed_schedule=None,
) -> GlobalFixedCashflowRvResult:
    """Compare a common-currency fixed rate against a fitted-curve yardstick."""
    fixed_view = bond_to_common_currency_fixed(
        asset_swap,
        curves,
        local_basis_swap=local_basis_swap,
        cross_currency_basis_swap=cross_currency_basis_swap,
        fixed_schedule=fixed_schedule,
    )
    target_maturity_years = fit_result.reference_date.days_between(fixed_view.maturity_date)
    benchmark = generate_constant_maturity_benchmark(
        fit_result,
        Decimal(target_maturity_years) / Decimal(365),
        coupon_rate=fixed_view.common_currency_fixed_rate,
        currency=fixed_view.target_currency,
    )
    residual = fixed_view.common_currency_fixed_rate - benchmark.fair_value_yield
    residual_bps = residual * Decimal("10000")
    threshold_value = _to_decimal(threshold_bps)
    return GlobalFixedCashflowRvResult(
        common_currency_fixed_rate=fixed_view.common_currency_fixed_rate,
        fitted_curve_yardstick=benchmark.fair_value_yield,
        residual=residual,
        residual_bps=residual_bps,
        classification=_classification(residual_bps, threshold_value),
        fixed_view=fixed_view,
    )


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
    measure = usd_sofr_adjusted_rv_measure(
        floating_view,
        yardstick_spread=yardstick_spread,
        adjusted_cds_spread=adjusted_cds_spread,
    )
    residual_bps = measure.residual_to_yardstick * Decimal("10000")
    threshold_value = _to_decimal(threshold_bps)
    return GlobalUsdSofrRvResult(
        usd_sofr_measure=measure,
        residual_bps=residual_bps,
        classification=_classification(residual_bps, threshold_value),
        floating_view=floating_view,
    )


__all__ = [
    "GlobalFixedCashflowRvResult",
    "GlobalUsdSofrRvResult",
    "global_fixed_cashflow_rv",
    "global_usd_sofr_rv",
]
