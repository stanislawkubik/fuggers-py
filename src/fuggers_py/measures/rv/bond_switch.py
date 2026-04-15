"""Bond-switch result records."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

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

__all__ = ["BondSwitchTrade"]
