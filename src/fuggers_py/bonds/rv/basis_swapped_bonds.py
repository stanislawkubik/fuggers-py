"""Bond transformations through asset-swap, basis, and CCBS chains.

The floating view chains asset-swap spread plus same-currency basis plus
cross-currency basis. The fixed view adds the target-currency par swap rate on
top of that common-currency floating spread.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import TYPE_CHECKING

from fuggers_py._core import PayReceive, Tenor
from fuggers_py._core.types import Currency, Date, Frequency
from fuggers_py._core.ids import InstrumentId
from fuggers_py.rates import (
    AssetSwap,
    BasisSwap,
    CrossCurrencyBasisSwap,
    FixedFloatSwap,
    FixedLegSpec,
    ScheduleDefinition,
)

if TYPE_CHECKING:
    from fuggers_py.rates import BasisSwapPricingResult, CrossCurrencyBasisSwapPricingResult


@dataclass(frozen=True, slots=True)
class CommonCurrencyFloatingBondView:
    """Common-currency floating-rate view of an asset-swap bond."""

    instrument_id: InstrumentId | None
    maturity_date: Date
    source_currency: Currency
    target_currency: Currency
    source_index_name: str
    source_index_tenor: Tenor
    target_index_name: str
    target_index_tenor: Tenor
    asset_swap_spread: Decimal
    same_currency_basis: Decimal
    cross_currency_basis: Decimal
    common_currency_floating_spread: Decimal
    asset_swap_result: object
    local_basis_result: BasisSwapPricingResult | None = None
    cross_currency_result: CrossCurrencyBasisSwapPricingResult | None = None


@dataclass(frozen=True, slots=True)
class CommonCurrencyFixedBondView:
    """Common-currency fixed-rate view derived from a floating view."""

    instrument_id: InstrumentId | None
    maturity_date: Date
    target_currency: Currency
    target_index_name: str
    target_index_tenor: Tenor
    par_swap_rate: Decimal
    common_currency_fixed_rate: Decimal
    floating_view: CommonCurrencyFloatingBondView


def _same_index(left, right) -> bool:
    return (
        left.currency == right.currency
        and left.index_name == right.index_name
        and left.index_tenor == right.index_tenor
    )


def bond_to_common_currency_floating(
    asset_swap: AssetSwap,
    curves: object,
    *,
    local_basis_swap: BasisSwap | None = None,
    cross_currency_basis_swap: CrossCurrencyBasisSwap | None = None,
) -> CommonCurrencyFloatingBondView:
    """Convert an asset-swap bond into a common-currency floating view."""
    from fuggers_py.rates import BasisSwapPricer, CrossCurrencyBasisSwapPricer
    from fuggers_py.rates.asset_swap_pricer import AssetSwapPricer

    asset_swap_result = AssetSwapPricer().price(asset_swap, curves)
    current_leg = asset_swap.floating_leg
    same_currency_basis = Decimal(0)
    local_basis_result: BasisSwapPricingResult | None = None
    cross_currency_basis = Decimal(0)
    cross_currency_result: CrossCurrencyBasisSwapPricingResult | None = None

    if local_basis_swap is not None:
        if local_basis_swap.quoted_leg is not PayReceive.RECEIVE:
            raise ValueError("bond_to_common_currency_floating requires local_basis_swap quoted on the receive leg.")
        if not _same_index(current_leg, local_basis_swap.pay_leg):
            raise ValueError("local_basis_swap pay_leg must match the asset-swap floating leg index and currency.")
        local_basis_result = BasisSwapPricer().price(local_basis_swap, curves)
        same_currency_basis = local_basis_result.par_spread
        current_leg = local_basis_swap.receive_leg

    if cross_currency_basis_swap is not None:
        if cross_currency_basis_swap.quoted_leg is not PayReceive.RECEIVE:
            raise ValueError("bond_to_common_currency_floating requires cross_currency_basis_swap quoted on the receive leg.")
        if not _same_index(current_leg, cross_currency_basis_swap.pay_leg):
            raise ValueError("cross_currency_basis_swap pay_leg must match the current floating reference leg.")
        cross_currency_result = CrossCurrencyBasisSwapPricer().price(cross_currency_basis_swap, curves)
        cross_currency_basis = cross_currency_result.par_spread
        current_leg = cross_currency_basis_swap.receive_leg

    return CommonCurrencyFloatingBondView(
        instrument_id=asset_swap.instrument_id,
        maturity_date=asset_swap.maturity_date(),
        source_currency=asset_swap.currency(),
        target_currency=current_leg.currency,
        source_index_name=asset_swap.floating_leg.index_name,
        source_index_tenor=asset_swap.floating_leg.index_tenor,
        target_index_name=current_leg.index_name,
        target_index_tenor=current_leg.index_tenor,
        asset_swap_spread=asset_swap_result.par_spread,
        same_currency_basis=same_currency_basis,
        cross_currency_basis=cross_currency_basis,
        common_currency_floating_spread=asset_swap_result.par_spread + same_currency_basis + cross_currency_basis,
        asset_swap_result=asset_swap_result,
        local_basis_result=local_basis_result,
        cross_currency_result=cross_currency_result,
    )


def bond_to_common_currency_fixed(
    asset_swap: AssetSwap,
    curves: object,
    *,
    local_basis_swap: BasisSwap | None = None,
    cross_currency_basis_swap: CrossCurrencyBasisSwap | None = None,
    fixed_schedule: ScheduleDefinition | None = None,
    fixed_frequency: Frequency = Frequency.SEMI_ANNUAL,
) -> CommonCurrencyFixedBondView:
    """Convert an asset-swap bond into a common-currency fixed view."""
    from fuggers_py.rates import SwapPricer

    floating_view = bond_to_common_currency_floating(
        asset_swap,
        curves,
        local_basis_swap=local_basis_swap,
        cross_currency_basis_swap=cross_currency_basis_swap,
    )
    resolved_fixed_schedule = fixed_schedule or ScheduleDefinition(frequency=fixed_frequency)
    current_leg = (
        cross_currency_basis_swap.receive_leg
        if cross_currency_basis_swap is not None
        else local_basis_swap.receive_leg if local_basis_swap is not None
        else asset_swap.floating_leg
    )
    synthetic_swap = FixedFloatSwap(
        effective_date=asset_swap.settlement_date,
        maturity_date=asset_swap.maturity_date(),
        fixed_leg=FixedLegSpec(
            pay_receive=PayReceive.RECEIVE,
            notional=Decimal("100"),
            fixed_rate=Decimal(0),
            currency=floating_view.target_currency,
            schedule=resolved_fixed_schedule,
        ),
        floating_leg=replace(current_leg, pay_receive=PayReceive.PAY),
    )
    par_swap_rate = SwapPricer().par_rate(synthetic_swap, curves)
    return CommonCurrencyFixedBondView(
        instrument_id=asset_swap.instrument_id,
        maturity_date=asset_swap.maturity_date(),
        target_currency=floating_view.target_currency,
        target_index_name=current_leg.index_name,
        target_index_tenor=current_leg.index_tenor,
        par_swap_rate=par_swap_rate,
        common_currency_fixed_rate=par_swap_rate + floating_view.common_currency_floating_spread,
        floating_view=floating_view,
    )


__all__ = [
    "CommonCurrencyFixedBondView",
    "CommonCurrencyFloatingBondView",
    "bond_to_common_currency_fixed",
    "bond_to_common_currency_floating",
]
