"""Tradable forward-rate agreements.

FRA rates are raw decimals and the PV is discounted to the FRA start date.
The optional rate index can be inferred from ``index_name`` and
``index_tenor`` when present, which keeps the contract usable both with
explicit curve metadata and with minimal market-data inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

from fuggers_py.reference.bonds.types import Tenor
from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Currency, Date
from fuggers_py.market.curves.multicurve import RateIndex
from fuggers_py.core.ids import InstrumentId
from fuggers_py.products.instruments import KindedInstrumentMixin

from .common import PayReceive


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _coerce_day_count(value: DayCountConvention | str) -> DayCountConvention:
    if isinstance(value, DayCountConvention):
        return value
    normalized = value.strip().upper().replace("/", "_")
    aliases = {
        "ACT360": DayCountConvention.ACT_360,
        "ACT_360": DayCountConvention.ACT_360,
        "ACT365F": DayCountConvention.ACT_365_FIXED,
        "ACT_365_FIXED": DayCountConvention.ACT_365_FIXED,
        "ACT365L": DayCountConvention.ACT_365_LEAP,
        "ACT_365_LEAP": DayCountConvention.ACT_365_LEAP,
        "30E_360": DayCountConvention.THIRTY_360_E,
        "30_360_E": DayCountConvention.THIRTY_360_E,
        "30_360_US": DayCountConvention.THIRTY_360_US,
    }
    if normalized in aliases:
        return aliases[normalized]
    return DayCountConvention[normalized]


@dataclass(frozen=True, slots=True)
class Fra(KindedInstrumentMixin):
    """Forward-rate agreement.

    Attributes
    ----------
    start_date, end_date:
        FRA accrual window.
    fixed_rate:
        Contract strike rate as a raw decimal.
    pay_receive:
        Direction of the payoff relative to the holder.
    index_name, index_tenor:
        Optional projection index metadata used for curve lookup.

    Notes
    -----
    ``fixed_rate`` and the premium conventions are raw decimals. The
    ``pay_receive`` flag describes the holder's payoff direction.
    """

    KIND: ClassVar[str] = "rates.fra"

    start_date: Date
    end_date: Date
    notional: Decimal
    fixed_rate: Decimal
    pay_receive: PayReceive | str = PayReceive.RECEIVE
    currency: Currency | str = Currency.USD
    day_count_convention: DayCountConvention | str = DayCountConvention.ACT_360
    index_name: str = "LIBOR"
    index_tenor: Tenor | str | None = None
    instrument_id: InstrumentId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "notional", _to_decimal(self.notional))
        object.__setattr__(self, "fixed_rate", _to_decimal(self.fixed_rate))
        object.__setattr__(self, "pay_receive", PayReceive.parse(self.pay_receive))
        if not isinstance(self.currency, Currency):
            object.__setattr__(self, "currency", Currency.from_code(str(self.currency)))
        object.__setattr__(self, "day_count_convention", _coerce_day_count(self.day_count_convention))
        object.__setattr__(self, "index_name", self.index_name.strip().upper())
        if self.index_tenor is not None and not isinstance(self.index_tenor, Tenor):
            object.__setattr__(self, "index_tenor", Tenor.parse(self.index_tenor))
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.end_date <= self.start_date:
            raise ValueError("Fra requires end_date after start_date.")
        if self.notional <= Decimal(0):
            raise ValueError("Fra notional must be positive.")
        if not self.index_name:
            raise ValueError("Fra index_name must be non-empty.")

    def year_fraction(self) -> Decimal:
        """Return the accrual factor between ``start_date`` and ``end_date``."""

        return self.day_count_convention.to_day_count().year_fraction(self.start_date, self.end_date)

    def rate_index(self) -> RateIndex | None:
        """Return the normalized rate index, if one is defined."""

        if self.index_tenor is None:
            return None
        return RateIndex.new(self.index_name, self.index_tenor, self.currency)


ForwardRateAgreement = Fra


__all__ = ["ForwardRateAgreement", "Fra"]
