"""Common leg specifications for tradable rates products.

The shared leg objects normalize schedule, currency, day-count, and pay/receive
conventions for swaps, FRAs, and basis trades. Coupon rates and spreads are
stored as raw decimals, so ``0.05`` means 5 percent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from fuggers_py._core.calendars import BusinessDayConvention
from fuggers_py._core.daycounts import DayCountConvention
from fuggers_py._core import CalendarId, Tenor
from fuggers_py._core.pay_receive import PayReceive as _PayReceive
from fuggers_py._core.types import Currency, Date, Frequency
from fuggers_py.bonds.cashflows import Schedule, ScheduleConfig
from fuggers_py._core.stub_rules import StubPeriodRules
from fuggers_py.curves.multicurve import RateIndex


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


def _coerce_calendar(value: CalendarId | str) -> CalendarId:
    if isinstance(value, CalendarId):
        return value
    return CalendarId.new(value)


def _coerce_business_day_convention(value: BusinessDayConvention | str) -> BusinessDayConvention:
    if isinstance(value, BusinessDayConvention):
        return value
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    return BusinessDayConvention[normalized]


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


def _coerce_currency(value: Currency | str) -> Currency:
    if isinstance(value, Currency):
        return value
    return Currency.from_code(str(value))


def _coerce_tenor(value: Tenor | str) -> Tenor:
    if isinstance(value, Tenor):
        return value
    return Tenor.parse(value)


@dataclass(frozen=True, slots=True)
class AccrualPeriod:
    """One accrual period in a generated schedule.

    Attributes
    ----------
    start_date:
        Unadjusted start date used for accrual calculation.
    end_date:
        Unadjusted end date used for accrual calculation.
    payment_date:
        Business-day-adjusted payment date.
    year_fraction:
        Day-count accrual factor for the period, stored as a raw decimal.
    """

    start_date: Date
    end_date: Date
    payment_date: Date
    year_fraction: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "year_fraction", _to_decimal(self.year_fraction))


@dataclass(frozen=True, slots=True)
class ScheduleDefinition:
    """Schedule-construction rules for rates legs.

    The definition wraps frequency, calendar, business-day convention, and stub
    handling so leg objects can generate accrual periods consistently.
    """

    frequency: Frequency | str = Frequency.QUARTERLY
    calendar: CalendarId | str = CalendarId.weekend_only()
    business_day_convention: BusinessDayConvention | str = BusinessDayConvention.MODIFIED_FOLLOWING
    end_of_month: bool = True
    stub_rules: StubPeriodRules = field(default_factory=StubPeriodRules.default)

    def __post_init__(self) -> None:
        object.__setattr__(self, "frequency", _coerce_frequency(self.frequency))
        object.__setattr__(self, "calendar", _coerce_calendar(self.calendar))
        object.__setattr__(
            self,
            "business_day_convention",
            _coerce_business_day_convention(self.business_day_convention),
        )

    def generate(self, start_date: Date, end_date: Date) -> Schedule:
        """Generate the adjusted schedule between two dates."""

        return Schedule.generate(
            ScheduleConfig(
                start_date=start_date,
                end_date=end_date,
                frequency=self.frequency,
                calendar=self.calendar,
                business_day_convention=self.business_day_convention,
                end_of_month=self.end_of_month,
                stub_rules=self.stub_rules,
            )
        )

    def accrual_periods(
        self,
        start_date: Date,
        end_date: Date,
        *,
        day_count_convention: DayCountConvention | str,
    ) -> tuple[AccrualPeriod, ...]:
        """Return accrual periods for the schedule.

        The accrual fraction is measured on the unadjusted schedule dates, while
        the payment date is the adjusted business-day date from the generated
        schedule.
        """

        schedule = self.generate(start_date, end_date)
        day_count = _coerce_day_count(day_count_convention).to_day_count()
        periods: list[AccrualPeriod] = []
        for index in range(1, len(schedule.unadjusted_dates)):
            accrual_start = schedule.unadjusted_dates[index - 1]
            accrual_end = schedule.unadjusted_dates[index]
            periods.append(
                AccrualPeriod(
                    start_date=accrual_start,
                    end_date=accrual_end,
                    payment_date=schedule.dates[index],
                    year_fraction=day_count.year_fraction(accrual_start, accrual_end),
                )
            )
        return tuple(periods)


@dataclass(frozen=True, slots=True)
class FixedLegSpec:
    """Fixed-rate cash-flow leg.

    Parameters
    ----------
    pay_receive:
        Direction of the leg cash flows.
    notional:
        Contract notional in currency units.
    fixed_rate:
        Coupon rate as a raw decimal.
    currency:
        Currency of the cash flows.
    day_count_convention:
        Day-count rule used to compute accrual factors.
    schedule:
        Schedule definition used to generate coupon dates.
    """

    pay_receive: _PayReceive | str
    notional: Decimal
    fixed_rate: Decimal
    currency: Currency | str = Currency.USD
    day_count_convention: DayCountConvention | str = DayCountConvention.ACT_365_FIXED
    schedule: ScheduleDefinition = field(
        default_factory=lambda: ScheduleDefinition(frequency=Frequency.SEMI_ANNUAL)
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "pay_receive", _PayReceive.parse(self.pay_receive))
        object.__setattr__(self, "notional", _to_decimal(self.notional))
        object.__setattr__(self, "fixed_rate", _to_decimal(self.fixed_rate))
        object.__setattr__(self, "currency", _coerce_currency(self.currency))
        object.__setattr__(self, "day_count_convention", _coerce_day_count(self.day_count_convention))
        if self.notional <= Decimal(0):
            raise ValueError("FixedLegSpec notional must be positive.")

    def accrual_periods(self, start_date: Date, end_date: Date) -> tuple[AccrualPeriod, ...]:
        """Return the fixed-leg accrual periods."""

        return self.schedule.accrual_periods(
            start_date,
            end_date,
            day_count_convention=self.day_count_convention,
        )


@dataclass(frozen=True, slots=True)
class FloatingLegSpec:
    """Floating-rate cash-flow leg.

    The floating coupon is ``forward + spread`` where both inputs are raw
    decimals. The leg is also normalized to a rate index for curve resolution.
    """

    pay_receive: _PayReceive | str
    notional: Decimal
    index_name: str
    index_tenor: Tenor | str
    spread: Decimal = Decimal(0)
    currency: Currency | str = Currency.USD
    day_count_convention: DayCountConvention | str = DayCountConvention.ACT_360
    schedule: ScheduleDefinition = field(
        default_factory=lambda: ScheduleDefinition(frequency=Frequency.QUARTERLY)
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "pay_receive", _PayReceive.parse(self.pay_receive))
        object.__setattr__(self, "notional", _to_decimal(self.notional))
        object.__setattr__(self, "spread", _to_decimal(self.spread))
        object.__setattr__(self, "index_name", self.index_name.strip().upper())
        object.__setattr__(self, "index_tenor", _coerce_tenor(self.index_tenor))
        object.__setattr__(self, "currency", _coerce_currency(self.currency))
        object.__setattr__(self, "day_count_convention", _coerce_day_count(self.day_count_convention))
        if not self.index_name:
            raise ValueError("FloatingLegSpec index_name must be non-empty.")
        if self.notional <= Decimal(0):
            raise ValueError("FloatingLegSpec notional must be positive.")

    def rate_index(self) -> RateIndex:
        """Return the normalized rate index for the leg."""

        return RateIndex.new(self.index_name, self.index_tenor, self.currency)

    def accrual_periods(self, start_date: Date, end_date: Date) -> tuple[AccrualPeriod, ...]:
        """Return the floating-leg accrual periods."""

        return self.schedule.accrual_periods(
            start_date,
            end_date,
            day_count_convention=self.day_count_convention,
        )


__all__ = [
    "AccrualPeriod",
    "FixedLegSpec",
    "FloatingLegSpec",
    "ScheduleDefinition",
]
