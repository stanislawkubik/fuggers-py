"""Government bond futures contract objects.

The contract stores the delivery window, contract economics, and the
standardized coupon/frequency used when computing conversion factors and
deliverable prices. Notional contract values are expressed in currency units;
quoted futures prices remain in percent of par.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

from fuggers_py._core.types import Currency, Date, Frequency
from fuggers_py._core.ids import InstrumentId, YearMonth
from fuggers_py.rates.instruments import KindedInstrumentMixin

from .reference import BondFutureContractReference


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _coerce_frequency(value: Frequency | str) -> Frequency:
    """Coerce a frequency label into a :class:`~fuggers_py._core.types.Frequency`.

    Common exchange-style aliases such as ``"semi"`` and ``"annual"`` are
    accepted in addition to enum names.
    """
    if isinstance(value, Frequency):
        return value
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "ANNUAL": Frequency.ANNUAL,
        "YEARLY": Frequency.ANNUAL,
        "SEMIANNUAL": Frequency.SEMI_ANNUAL,
        "SEMI_ANNUAL": Frequency.SEMI_ANNUAL,
        "SEMI": Frequency.SEMI_ANNUAL,
        "QUARTERLY": Frequency.QUARTERLY,
        "QUARTER": Frequency.QUARTERLY,
        "MONTHLY": Frequency.MONTHLY,
        "MONTH": Frequency.MONTHLY,
        "ZERO": Frequency.ZERO,
    }
    if normalized in aliases:
        return aliases[normalized]
    return Frequency[normalized]


@dataclass(frozen=True, slots=True)
class GovernmentBondFuture(KindedInstrumentMixin):
    """Government bond futures contract metadata.

    Parameters
    ----------
    delivery_date, first_delivery_date, last_delivery_date
        Delivery anchors for the contract. At least one delivery anchor or a
        ``delivery_month`` must be supplied.
    instrument_id
        Stable instrument identifier for the listed contract.
    currency
        Contract currency.
    delivery_month
        Delivery month if the exact first/last delivery dates are not known.
    contract_size
        Currency notional per contract.
    tick_size
        Minimum price increment in percent of par.
    standard_coupon_rate
        Standardized coupon rate used for conversion-factor calculations as a
        raw decimal, for example ``Decimal("0.06")`` for 6%.
    coupon_frequency
        Coupon frequency of the standardized deliverable bond.
    exchange
        Optional exchange code normalized to upper case.

    Notes
    -----
    Delivery anchors are intentionally flexible because the reference data may
    provide either a single delivery date, a delivery window, or only a
    delivery month. Contract prices remain quoted in percent of par.
    """
    KIND: ClassVar[str] = "rates.future.government_bond"

    delivery_date: Date | None = None
    first_delivery_date: Date | None = None
    last_delivery_date: Date | None = None
    instrument_id: InstrumentId | None = None
    currency: Currency | str = Currency.USD
    delivery_month: YearMonth | str | None = None
    contract_size: Decimal = Decimal("100000")
    tick_size: Decimal = Decimal("0.015625")
    standard_coupon_rate: Decimal = Decimal("0.06")
    coupon_frequency: Frequency | str = Frequency.SEMI_ANNUAL
    exchange: str | None = None

    def __post_init__(self) -> None:
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if not isinstance(self.currency, Currency):
            object.__setattr__(self, "currency", Currency.from_code(str(self.currency)))
        if self.delivery_month is not None and not isinstance(self.delivery_month, YearMonth):
            object.__setattr__(self, "delivery_month", YearMonth.parse(self.delivery_month))
        object.__setattr__(self, "contract_size", _to_decimal(self.contract_size))
        object.__setattr__(self, "tick_size", _to_decimal(self.tick_size))
        object.__setattr__(self, "standard_coupon_rate", _to_decimal(self.standard_coupon_rate))
        object.__setattr__(self, "coupon_frequency", _coerce_frequency(self.coupon_frequency))
        if self.exchange is not None:
            object.__setattr__(self, "exchange", self.exchange.strip().upper())
        if self.contract_size <= Decimal(0):
            raise ValueError("GovernmentBondFuture contract_size must be positive.")
        if self.tick_size <= Decimal(0):
            raise ValueError("GovernmentBondFuture tick_size must be positive.")
        if self.standard_coupon_rate < Decimal(0):
            raise ValueError("GovernmentBondFuture standard_coupon_rate must be non-negative.")
        if self.first_delivery_date is not None and self.last_delivery_date is not None:
            if self.last_delivery_date < self.first_delivery_date:
                raise ValueError("GovernmentBondFuture requires last_delivery_date on or after first_delivery_date.")
        if self.delivery_date is None and self.first_delivery_date is None and self.last_delivery_date is None:
            if self.delivery_month is None:
                raise ValueError(
                    "GovernmentBondFuture requires delivery_date, delivery window, or delivery_month."
                )
        if self.delivery_date is not None and self.first_delivery_date is not None:
            if self.delivery_date < self.first_delivery_date:
                raise ValueError("GovernmentBondFuture delivery_date cannot precede first_delivery_date.")
        if self.delivery_date is not None and self.last_delivery_date is not None:
            if self.delivery_date > self.last_delivery_date:
                raise ValueError("GovernmentBondFuture delivery_date cannot exceed last_delivery_date.")

    @classmethod
    def from_reference(
        cls,
        reference: BondFutureContractReference,
        *,
        delivery_date: Date | None = None,
    ) -> "GovernmentBondFuture":
        """Build a contract from reference data."""
        return cls(
            delivery_date=delivery_date,
            first_delivery_date=reference.first_delivery_date,
            last_delivery_date=reference.last_delivery_date or reference.final_delivery_date,
            instrument_id=reference.instrument_id,
            currency=reference.currency,
            delivery_month=reference.delivery_month,
            contract_size=reference.contract_size or Decimal("100000"),
            tick_size=reference.tick_size or Decimal("0.015625"),
            standard_coupon_rate=reference.standard_coupon_rate or Decimal("0.06"),
            coupon_frequency=reference.coupon_frequency or Frequency.SEMI_ANNUAL,
            exchange=reference.exchange,
        )

    def resolved_delivery_date(self) -> Date:
        """Return the best available delivery date anchor for the contract."""
        if self.delivery_date is not None:
            return self.delivery_date
        if self.first_delivery_date is not None:
            return self.first_delivery_date
        if self.last_delivery_date is not None:
            return self.last_delivery_date
        if self.delivery_month is None:
            raise ValueError("GovernmentBondFuture has no delivery date anchor.")
        return Date.from_ymd(self.delivery_month.year, self.delivery_month.month, 1)

    def tick_value(self) -> Decimal:
        """Return the currency value of one tick."""
        return self.contract_size * self.tick_size / Decimal(100)


__all__ = ["GovernmentBondFuture"]
