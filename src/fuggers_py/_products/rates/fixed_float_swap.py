"""Tradable fixed-float swaps.

The fixed and floating legs must share a currency, run on the same accrual
window, and point in opposite directions. Coupon rates and spreads are stored
as raw decimals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from fuggers_py._core.types import Date
from fuggers_py._core.ids import InstrumentId
from fuggers_py._products.instruments import KindedInstrumentMixin

from .common import FixedLegSpec, FloatingLegSpec


@dataclass(frozen=True, slots=True)
class FixedFloatSwap(KindedInstrumentMixin):
    """Plain fixed-for-floating interest-rate swap.

    Parameters
    ----------
    effective_date, maturity_date:
        Contract start and end dates. ``maturity_date`` must be after
        ``effective_date``.
    fixed_leg, floating_leg:
        Leg specifications sharing the same currency and opposite
        pay/receive directions.
    instrument_id:
        Optional stable identifier for the swap.
    """

    KIND: ClassVar[str] = "rates.swap.fixed_float"

    effective_date: Date
    maturity_date: Date
    fixed_leg: FixedLegSpec
    floating_leg: FloatingLegSpec
    instrument_id: InstrumentId | None = None

    def __post_init__(self) -> None:
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.maturity_date <= self.effective_date:
            raise ValueError("FixedFloatSwap requires maturity_date after effective_date.")
        if self.fixed_leg.currency is not self.floating_leg.currency:
            raise ValueError("FixedFloatSwap requires fixed and floating legs in the same currency.")
        if self.fixed_leg.pay_receive is self.floating_leg.pay_receive:
            raise ValueError("FixedFloatSwap fixed and floating legs must have opposite directions.")

    def currency(self):
        """Return the common swap currency."""

        return self.fixed_leg.currency

    def fixed_periods(self):
        """Return the fixed-leg accrual periods."""

        return self.fixed_leg.accrual_periods(self.effective_date, self.maturity_date)

    def floating_periods(self):
        """Return the floating-leg accrual periods."""

        return self.floating_leg.accrual_periods(self.effective_date, self.maturity_date)


InterestRateSwap = FixedFloatSwap


__all__ = ["FixedFloatSwap", "InterestRateSwap"]
