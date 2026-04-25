"""Swaption product definitions.

The exercise direction follows the usual market convention: payer swaptions
are calls on the underlying swap rate and receiver swaptions are puts.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

from fuggers_py._core import OptionType, PayReceive
from fuggers_py._core.types import Date
from fuggers_py._core.ids import InstrumentId
from fuggers_py.rates.instruments import KindedInstrumentMixin

from ..fixed_float_swap import FixedFloatSwap
from ._product_common import _to_decimal


@dataclass(frozen=True, slots=True)
class Swaption(KindedInstrumentMixin):
    """European swaption on a fixed-float underlying swap.

    Parameters
    ----------
    expiry_date:
        Option expiry date.
    underlying_swap:
        Fixed-float swap that becomes effective if the option is exercised.
    strike:
        Exercise strike as a raw decimal.
    exercise_into:
        Direction of the underlying swap entered at exercise.
    instrument_id:
        Optional stable identifier for the swaption.
    cash_settled:
        Whether the option is cash settled instead of physically exercised.
    """

    KIND: ClassVar[str] = "rates.option.swaption"

    expiry_date: Date
    underlying_swap: FixedFloatSwap
    strike: Decimal
    exercise_into: PayReceive | str = PayReceive.PAY
    instrument_id: InstrumentId | None = None
    cash_settled: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "strike", _to_decimal(self.strike))
        object.__setattr__(self, "exercise_into", PayReceive.parse(self.exercise_into))
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.strike < Decimal(0):
            raise ValueError("Swaption strike must be non-negative.")
        if self.expiry_date > self.underlying_swap.effective_date:
            raise ValueError("Swaption expiry_date must be on or before the underlying swap effective_date.")

    def currency(self):
        """Return the underlying swap currency."""
        return self.underlying_swap.currency()

    @property
    def underlying(self) -> FixedFloatSwap:
        """Return the underlying swap."""
        return self.underlying_swap

    def option_type(self) -> OptionType:
        """Return the call/put type implied by the exercise direction."""
        return OptionType.CALL if self.exercise_into is PayReceive.PAY else OptionType.PUT


__all__ = ["Swaption"]
