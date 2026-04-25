"""Credit-default swap instruments."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import ClassVar

from fuggers_py._core import (
    BusinessDayConvention,
    CalendarId,
    Currency,
    Date,
    DayCountConvention,
    Frequency,
    InstrumentId,
)
from fuggers_py.bonds import Schedule, ScheduleConfig


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _coerce_currency(value: Currency | str) -> Currency:
    if isinstance(value, Currency):
        return value
    return Currency.from_code(str(value))


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


def _coerce_calendar(value: CalendarId | str) -> CalendarId:
    if isinstance(value, CalendarId):
        return value
    return CalendarId.new(value)


def _coerce_business_day_convention(value: BusinessDayConvention | str) -> BusinessDayConvention:
    if isinstance(value, BusinessDayConvention):
        return value
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    return BusinessDayConvention[normalized]


class _KindedInstrumentMixin:
    KIND: ClassVar[str]

    @property
    def kind(self) -> str:
        return self.KIND


class _StubType(str, Enum):
    FRONT_SHORT = "FRONT_SHORT"
    FRONT_LONG = "FRONT_LONG"
    BACK_SHORT = "BACK_SHORT"
    BACK_LONG = "BACK_LONG"

    def is_front_stub(self) -> bool:
        return self in {_StubType.FRONT_SHORT, _StubType.FRONT_LONG}


@dataclass(frozen=True, slots=True)
class _StubPeriodRules:
    stub_type: _StubType | None = None
    first_regular_date: Date | None = None
    penultimate_date: Date | None = None

    @classmethod
    def default(cls) -> "_StubPeriodRules":
        return cls()


class ProtectionSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

    @classmethod
    def parse(cls, value: "ProtectionSide" | str) -> "ProtectionSide":
        if isinstance(value, cls):
            return value
        normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
        aliases = {
            "BUY": cls.BUY,
            "BUY_PROTECTION": cls.BUY,
            "PROTECTION_BUYER": cls.BUY,
            "SELL": cls.SELL,
            "SELL_PROTECTION": cls.SELL,
            "PROTECTION_SELLER": cls.SELL,
        }
        try:
            return aliases[normalized]
        except KeyError as exc:
            raise ValueError(f"Unsupported protection side: {value!r}.") from exc

    def sign(self) -> Decimal:
        return Decimal(1) if self is ProtectionSide.BUY else Decimal(-1)

    def opposite(self) -> "ProtectionSide":
        return ProtectionSide.SELL if self is ProtectionSide.BUY else ProtectionSide.BUY


@dataclass(frozen=True, slots=True)
class CdsPremiumPeriod:
    start_date: Date
    end_date: Date
    payment_date: Date
    year_fraction: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "year_fraction", _to_decimal(self.year_fraction))


@dataclass(frozen=True, slots=True)
class CreditDefaultSwap(_KindedInstrumentMixin):
    KIND: ClassVar[str] = "credit.cds"

    effective_date: Date
    maturity_date: Date
    running_spread: Decimal
    notional: Decimal = Decimal(1_000_000)
    protection_side: ProtectionSide | str = ProtectionSide.BUY
    recovery_rate: Decimal = Decimal("0.4")
    currency: Currency | str = Currency.USD
    payment_frequency: Frequency | str = Frequency.QUARTERLY
    day_count_convention: DayCountConvention | str = DayCountConvention.ACT_360
    calendar: CalendarId | str = field(default_factory=CalendarId.weekend_only)
    business_day_convention: BusinessDayConvention | str = BusinessDayConvention.MODIFIED_FOLLOWING
    end_of_month: bool = True
    stub_rules: object = field(default_factory=_StubPeriodRules.default)
    accrued_on_default_fraction: Decimal = Decimal("0.5")
    upfront: Decimal = Decimal(0)
    settlement_date: Date | None = None
    reference_entity: str | None = None
    instrument_id: InstrumentId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "running_spread", _to_decimal(self.running_spread))
        object.__setattr__(self, "notional", _to_decimal(self.notional))
        object.__setattr__(self, "protection_side", ProtectionSide.parse(self.protection_side))
        object.__setattr__(self, "recovery_rate", _to_decimal(self.recovery_rate))
        object.__setattr__(self, "currency", _coerce_currency(self.currency))
        object.__setattr__(self, "payment_frequency", _coerce_frequency(self.payment_frequency))
        object.__setattr__(self, "day_count_convention", _coerce_day_count(self.day_count_convention))
        object.__setattr__(self, "calendar", _coerce_calendar(self.calendar))
        object.__setattr__(
            self,
            "business_day_convention",
            _coerce_business_day_convention(self.business_day_convention),
        )
        object.__setattr__(self, "accrued_on_default_fraction", _to_decimal(self.accrued_on_default_fraction))
        object.__setattr__(self, "upfront", _to_decimal(self.upfront))
        if self.reference_entity is not None:
            object.__setattr__(self, "reference_entity", self.reference_entity.strip())
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.maturity_date <= self.effective_date:
            raise ValueError("CreditDefaultSwap requires maturity_date after effective_date.")
        if self.notional <= Decimal(0):
            raise ValueError("CreditDefaultSwap notional must be positive.")
        if self.payment_frequency.is_zero():
            raise ValueError("CreditDefaultSwap payment_frequency must be non-zero.")
        if self.recovery_rate < Decimal(0) or self.recovery_rate >= Decimal(1):
            raise ValueError("CreditDefaultSwap recovery_rate must lie in [0, 1).")
        if self.accrued_on_default_fraction < Decimal(0) or self.accrued_on_default_fraction > Decimal(1):
            raise ValueError("accrued_on_default_fraction must lie in [0, 1].")

    def schedule(self) -> Schedule:
        return Schedule.generate(
            ScheduleConfig(
                start_date=self.effective_date,
                end_date=self.maturity_date,
                frequency=self.payment_frequency,
                calendar=self.calendar,
                business_day_convention=self.business_day_convention,
                end_of_month=self.end_of_month,
                stub_rules=self.stub_rules,
            )
        )

    def premium_periods(self) -> tuple[CdsPremiumPeriod, ...]:
        schedule = self.schedule()
        day_count = self.day_count_convention.to_day_count()
        periods: list[CdsPremiumPeriod] = []
        for index in range(1, len(schedule.unadjusted_dates)):
            accrual_start = schedule.unadjusted_dates[index - 1]
            accrual_end = schedule.unadjusted_dates[index]
            periods.append(
                CdsPremiumPeriod(
                    start_date=accrual_start,
                    end_date=accrual_end,
                    payment_date=schedule.dates[index],
                    year_fraction=day_count.year_fraction(accrual_start, accrual_end),
                )
            )
        return tuple(periods)

    def loss_given_default(self) -> Decimal:
        return Decimal(1) - self.recovery_rate

    def upfront_amount(self) -> Decimal:
        return self.notional * self.upfront


Cds = CreditDefaultSwap


__all__ = [
    "Cds",
    "CdsPremiumPeriod",
    "CreditDefaultSwap",
    "ProtectionSide",
]
