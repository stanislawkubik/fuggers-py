"""Reference records owned by rates futures."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import TYPE_CHECKING

from fuggers_py._core import YieldCalculationRules
from fuggers_py._core.ids import InstrumentId, YearMonth
from fuggers_py._core.types import Currency, Date, Frequency

if TYPE_CHECKING:
    from fuggers_py.bonds.instruments import FixedBond


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _coerce_frequency(value: Frequency | str) -> Frequency:
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
class BondFutureReferenceData:
    """Reference metadata for a government bond futures contract."""

    instrument_id: InstrumentId
    currency: Currency = Currency.USD
    delivery_month: YearMonth | str | None = None
    contract_size: Decimal | None = None
    tick_size: Decimal | None = None
    exchange: str | None = None
    first_delivery_date: Date | None = None
    last_delivery_date: Date | None = None
    final_delivery_date: Date | None = None
    standard_coupon_rate: Decimal | None = None
    coupon_frequency: Frequency | str | None = None
    underlying_basket: tuple[InstrumentId, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.delivery_month is not None:
            object.__setattr__(self, "delivery_month", YearMonth.parse(self.delivery_month))
        if self.exchange is not None:
            object.__setattr__(self, "exchange", self.exchange.strip().upper())
        object.__setattr__(self, "underlying_basket", tuple(InstrumentId.parse(item) for item in self.underlying_basket))
        if self.contract_size is not None:
            object.__setattr__(self, "contract_size", _to_decimal(self.contract_size))
        if self.tick_size is not None:
            object.__setattr__(self, "tick_size", _to_decimal(self.tick_size))
        if self.standard_coupon_rate is not None:
            object.__setattr__(self, "standard_coupon_rate", _to_decimal(self.standard_coupon_rate))
        if self.coupon_frequency is not None:
            object.__setattr__(self, "coupon_frequency", _coerce_frequency(self.coupon_frequency))
        if self.first_delivery_date is not None and self.last_delivery_date is not None:
            if self.last_delivery_date < self.first_delivery_date:
                raise ValueError("BondFutureReferenceData requires last_delivery_date on or after first_delivery_date.")
        if self.final_delivery_date is not None and self.last_delivery_date is not None:
            if self.final_delivery_date < self.last_delivery_date:
                raise ValueError("BondFutureReferenceData requires final_delivery_date on or after last_delivery_date.")


BondFutureContractReference = BondFutureReferenceData


FutureReferenceData = BondFutureReferenceData


@dataclass(frozen=True, slots=True)
class DeliverableBondReference:
    """Deliverable bond metadata for a government bond futures basket."""

    instrument_id: InstrumentId
    issue_date: Date
    maturity_date: Date
    coupon_rate: Decimal
    currency: Currency = Currency.USD
    frequency: Frequency | str = Frequency.SEMI_ANNUAL
    notional: Decimal = Decimal(100)
    yield_rules: YieldCalculationRules | None = None
    published_conversion_factor: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        object.__setattr__(self, "coupon_rate", _to_decimal(self.coupon_rate))
        object.__setattr__(self, "frequency", _coerce_frequency(self.frequency))
        object.__setattr__(self, "notional", _to_decimal(self.notional))
        if self.published_conversion_factor is not None:
            object.__setattr__(
                self,
                "published_conversion_factor",
                _to_decimal(self.published_conversion_factor),
            )
        if self.maturity_date <= self.issue_date:
            raise ValueError("DeliverableBondReference requires maturity_date after issue_date.")
        if self.notional <= Decimal(0):
            raise ValueError("DeliverableBondReference notional must be positive.")

    def to_instrument(self) -> FixedBond:
        """Convert the deliverable reference into a fixed-coupon bond."""
        from fuggers_py.bonds.instruments import FixedBondBuilder

        frequency = _coerce_frequency(self.frequency)
        rules = self.yield_rules
        if rules is None:
            rules = YieldCalculationRules.us_treasury()
            if rules.frequency is not frequency:
                rules = replace(rules, frequency=frequency)
        elif rules.frequency is not frequency:
            rules = replace(rules, frequency=frequency)
        return (
            FixedBondBuilder.new()
            .with_issue_date(self.issue_date)
            .with_maturity_date(self.maturity_date)
            .with_coupon_rate(self.coupon_rate)
            .with_frequency(frequency)
            .with_currency(self.currency)
            .with_notional(self.notional)
            .with_instrument_id(self.instrument_id)
            .with_rules(rules)
            .build()
        )


__all__ = [
    "BondFutureContractReference",
    "BondFutureReferenceData",
    "DeliverableBondReference",
    "FutureReferenceData",
]
