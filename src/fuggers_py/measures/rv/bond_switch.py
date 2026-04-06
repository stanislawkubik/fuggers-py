"""Bond-switch construction from local rich/cheap signals.

The trade buys the cheap bond and sells the rich bond. Expected convergence is
positive when the cheap bond cheapens less than the rich bond richens.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.pricers.bonds.risk import RiskMetrics
from fuggers_py.reference.bonds.types import CompoundingKind
from fuggers_py.core.types import Compounding, Yield
from fuggers_py.market.curves.fitted_bonds import FittedBondCurve

from .rich_cheap import rank_rich_cheap


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _yield_from_decimal(bond, yield_value: Decimal) -> Yield:
    method = bond.rules().compounding
    if method.kind is CompoundingKind.CONTINUOUS:
        compounding = Compounding.CONTINUOUS
    elif method.kind in {CompoundingKind.SIMPLE, CompoundingKind.DISCOUNT}:
        compounding = Compounding.SIMPLE
    elif method.frequency == 1:
        compounding = Compounding.ANNUAL
    elif method.frequency == 2:
        compounding = Compounding.SEMI_ANNUAL
    elif method.frequency == 4:
        compounding = Compounding.QUARTERLY
    else:
        compounding = Compounding.ANNUAL
    return Yield.new(yield_value, compounding)


@dataclass(frozen=True, slots=True)
class BondSwitchTrade:
    """DV01-hedged bond-switch trade summary."""

    cheap_instrument_id: object
    rich_instrument_id: object
    buy_notional: Decimal
    sell_notional: Decimal
    duration_hedge_ratio: Decimal
    expected_price_convergence: Decimal
    expected_bp_convergence: Decimal


def construct_bond_switch(
    fit_result: FittedBondCurve,
    *,
    cheap_instrument_id: object | None = None,
    rich_instrument_id: object | None = None,
    base_notional: object = Decimal("1000000"),
) -> BondSwitchTrade:
    """Construct a bond-switch trade from a fitted-bond curve."""
    ranking = rank_rich_cheap(fit_result)
    cheap_id = cheap_instrument_id or ranking[0].instrument_id
    rich_id = rich_instrument_id or ranking[-1].instrument_id
    cheap = fit_result.get_bond(cheap_id)
    rich = fit_result.get_bond(rich_id)

    cheap_dv01 = RiskMetrics.from_bond(
        cheap["bond"],
        _yield_from_decimal(cheap["bond"], _to_decimal(cheap["fitted_yield"])),
        fit_result.reference_date,
    ).dv01
    rich_dv01 = RiskMetrics.from_bond(
        rich["bond"],
        _yield_from_decimal(rich["bond"], _to_decimal(rich["fitted_yield"])),
        fit_result.reference_date,
    ).dv01
    if rich_dv01 == Decimal(0):
        raise ValueError("construct_bond_switch requires a non-zero rich-bond DV01.")
    buy_notional = _to_decimal(base_notional)
    duration_hedge_ratio = cheap_dv01 / rich_dv01
    sell_notional = buy_notional * duration_hedge_ratio
    expected_price_convergence = (buy_notional / Decimal(100)) * (-_to_decimal(cheap["price_residual"])) + (
        sell_notional / Decimal(100)
    ) * _to_decimal(rich["price_residual"])
    expected_bp_convergence = _to_decimal(cheap["bp_residual"]) - _to_decimal(rich["bp_residual"])
    return BondSwitchTrade(
        cheap_instrument_id=cheap["instrument_id"],
        rich_instrument_id=rich["instrument_id"],
        buy_notional=buy_notional,
        sell_notional=sell_notional,
        duration_hedge_ratio=duration_hedge_ratio,
        expected_price_convergence=expected_price_convergence,
        expected_bp_convergence=expected_bp_convergence,
    )


__all__ = ["BondSwitchTrade", "construct_bond_switch"]
