"""Bond-switch construction from local rich/cheap signals.

The trade buys the cheap bond and sells the rich bond. Expected convergence is
positive when the cheap bond cheapens less than the rich bond richens.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.market.curves.fitted_bonds import BondCurve

from ._shared import to_decimal
from .neutrality import neutralize_bond_pair
from .rich_cheap import rank_rich_cheap

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
    fit_result: BondCurve,
    *,
    cheap_instrument_id: object | None = None,
    rich_instrument_id: object | None = None,
    base_notional: object = Decimal("1000000"),
) -> BondSwitchTrade:
    """Construct a bond-switch trade from a fitted-bond curve."""
    ranking = rank_rich_cheap(fit_result)
    cheap_id = cheap_instrument_id or ranking[0].instrument_id
    rich_id = rich_instrument_id or ranking[-1].instrument_id
    trade = neutralize_bond_pair(
        fit_result,
        long_instrument_id=cheap_id,
        short_instrument_id=rich_id,
        base_long_notional=to_decimal(base_notional),
    )
    return BondSwitchTrade(
        cheap_instrument_id=trade.long_leg.instrument_id,
        rich_instrument_id=trade.short_leg.instrument_id,
        buy_notional=trade.long_leg.notional,
        sell_notional=trade.short_leg.notional,
        duration_hedge_ratio=trade.hedge_ratio,
        expected_price_convergence=trade.expected_price_convergence,
        expected_bp_convergence=trade.expected_bp_convergence,
    )


__all__ = ["BondSwitchTrade", "construct_bond_switch"]
