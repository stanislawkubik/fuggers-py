"""Options on government bond futures.

The strike is quoted in futures price points, not in yield terms. The option
contract multiplier inherits the underlying futures contract size divided by
100 because futures prices are quoted in percent of par.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

from fuggers_py._core import OptionType
from fuggers_py._core.types import Date
from fuggers_py._core.ids import InstrumentId
from fuggers_py.rates.instruments import KindedInstrumentMixin

from ..futures.government_bond_future import GovernmentBondFuture
from ._product_common import _to_decimal


@dataclass(frozen=True, slots=True)
class FuturesOption(KindedInstrumentMixin):
    """Option on a government bond futures contract.

    Parameters
    ----------
    expiry_date:
        Option expiry date.
    underlying_future:
        Government bond futures contract referenced by the option.
    strike:
        Futures price strike in price points.
    option_type:
        Call or put direction of the option.
    instrument_id:
        Optional stable identifier for the option.
    """

    KIND: ClassVar[str] = "rates.option.futures"

    expiry_date: Date
    underlying_future: GovernmentBondFuture
    strike: Decimal
    option_type: OptionType | str = OptionType.CALL
    instrument_id: InstrumentId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "strike", _to_decimal(self.strike))
        object.__setattr__(self, "option_type", OptionType.parse(self.option_type))
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.strike <= Decimal(0):
            raise ValueError("FuturesOption strike must be positive.")
        if self.expiry_date > self.underlying_future.resolved_delivery_date():
            raise ValueError("FuturesOption expiry_date must be on or before the underlying delivery date.")

    def currency(self):
        """Return the underlying futures currency."""
        return self.underlying_future.currency

    @property
    def underlying(self) -> GovernmentBondFuture:
        """Return the underlying futures contract."""
        return self.underlying_future

    def contract_multiplier(self) -> Decimal:
        """Return the currency value of one futures price point."""
        return self.underlying_future.contract_size / Decimal(100)


__all__ = ["FuturesOption"]
