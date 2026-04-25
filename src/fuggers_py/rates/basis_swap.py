"""Tradable same-currency basis swaps.

The quoted leg is the leg whose spread is calibrated in pricing. Spreads are
raw decimals and both legs must be in the same currency. The leg directions
are explicit so the sign convention is unambiguous.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from fuggers_py._core import PayReceive
from fuggers_py._core.types import Date
from fuggers_py._core.ids import InstrumentId
from fuggers_py.rates.instruments import KindedInstrumentMixin

from .common import FloatingLegSpec


@dataclass(frozen=True, slots=True)
class BasisSwap(KindedInstrumentMixin):
    """Same-currency floating-versus-floating basis swap.

    Parameters
    ----------
    effective_date, maturity_date:
        Contract start and end dates.
    pay_leg, receive_leg:
        Floating-leg specifications for the two swap legs.
    quoted_leg:
        Leg whose spread is the market quote.
    instrument_id:
        Optional stable identifier for the swap.
    """

    KIND: ClassVar[str] = "rates.swap.basis"

    effective_date: Date
    maturity_date: Date
    pay_leg: FloatingLegSpec
    receive_leg: FloatingLegSpec
    quoted_leg: PayReceive | str = PayReceive.RECEIVE
    instrument_id: InstrumentId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "quoted_leg", PayReceive.parse(self.quoted_leg))
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.maturity_date <= self.effective_date:
            raise ValueError("BasisSwap requires maturity_date after effective_date.")
        if self.pay_leg.currency is not self.receive_leg.currency:
            raise ValueError("BasisSwap requires both legs in the same currency.")
        if self.pay_leg.pay_receive is not PayReceive.PAY:
            raise ValueError("BasisSwap pay_leg must be marked as PAY.")
        if self.receive_leg.pay_receive is not PayReceive.RECEIVE:
            raise ValueError("BasisSwap receive_leg must be marked as RECEIVE.")

    def currency(self):
        """Return the common swap currency."""

        return self.pay_leg.currency

    def pay_periods(self):
        """Return the pay-leg accrual periods."""

        return self.pay_leg.accrual_periods(self.effective_date, self.maturity_date)

    def receive_periods(self):
        """Return the receive-leg accrual periods."""

        return self.receive_leg.accrual_periods(self.effective_date, self.maturity_date)

    def quoted_leg_spec(self) -> FloatingLegSpec:
        """Return the leg whose spread is quoted."""

        return self.receive_leg if self.quoted_leg is PayReceive.RECEIVE else self.pay_leg


SameCurrencyBasisSwap = BasisSwap


__all__ = ["BasisSwap", "SameCurrencyBasisSwap"]
