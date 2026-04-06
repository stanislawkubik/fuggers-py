"""Tradable cross-currency basis swaps.

The FX spot rate is quoted as receive-currency units per one pay-currency
unit. Spreads are raw decimals and principal exchanges are optional. The
quoted leg identifies which spread is calibrated in pricing.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

from fuggers_py.core.types import Date
from fuggers_py.core.ids import CurrencyPair, InstrumentId
from fuggers_py.products.instruments import KindedInstrumentMixin

from .common import FloatingLegSpec, PayReceive


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class CrossCurrencyBasisSwap(KindedInstrumentMixin):
    """Cross-currency floating-versus-floating basis swap.

    Parameters
    ----------
    effective_date, maturity_date:
        Contract start and end dates.
    pay_leg, receive_leg:
        Floating-leg specifications for the two currencies.
    spot_fx_rate:
        Spot FX quote expressed as receive-currency units per one pay-currency
        unit.
    quoted_leg:
        Leg whose spread is the market quote.
    initial_exchange, final_exchange:
        Whether principal is exchanged at the start and end of the swap.
    instrument_id:
        Optional stable identifier for the swap.
    """

    KIND: ClassVar[str] = "rates.swap.cross_currency_basis"

    effective_date: Date
    maturity_date: Date
    pay_leg: FloatingLegSpec
    receive_leg: FloatingLegSpec
    spot_fx_rate: Decimal
    quoted_leg: PayReceive | str = PayReceive.RECEIVE
    initial_exchange: bool = True
    final_exchange: bool = True
    instrument_id: InstrumentId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "spot_fx_rate", _to_decimal(self.spot_fx_rate))
        object.__setattr__(self, "quoted_leg", PayReceive.parse(self.quoted_leg))
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.maturity_date <= self.effective_date:
            raise ValueError("CrossCurrencyBasisSwap requires maturity_date after effective_date.")
        if self.pay_leg.currency is self.receive_leg.currency:
            raise ValueError("CrossCurrencyBasisSwap requires different leg currencies.")
        if self.pay_leg.pay_receive is not PayReceive.PAY:
            raise ValueError("CrossCurrencyBasisSwap pay_leg must be marked as PAY.")
        if self.receive_leg.pay_receive is not PayReceive.RECEIVE:
            raise ValueError("CrossCurrencyBasisSwap receive_leg must be marked as RECEIVE.")
        if self.spot_fx_rate <= Decimal(0):
            raise ValueError("CrossCurrencyBasisSwap spot_fx_rate must be positive.")

    def currency_pair(self) -> CurrencyPair:
        """Return the pay/receive currency pair."""

        return CurrencyPair(base=self.pay_leg.currency, quote=self.receive_leg.currency)

    def pay_periods(self):
        """Return the pay-leg accrual periods."""

        return self.pay_leg.accrual_periods(self.effective_date, self.maturity_date)

    def receive_periods(self):
        """Return the receive-leg accrual periods."""

        return self.receive_leg.accrual_periods(self.effective_date, self.maturity_date)

    def quoted_leg_spec(self) -> FloatingLegSpec:
        """Return the leg whose spread is quoted."""

        return self.receive_leg if self.quoted_leg is PayReceive.RECEIVE else self.pay_leg


__all__ = ["CrossCurrencyBasisSwap"]
