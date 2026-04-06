"""Standard coupon inflation swaps.

The fixed and inflation-linked legs run over a schedule of aligned accrual
periods. The fixed leg uses a raw-decimal coupon and the inflation leg settles
the realized CPI change over each period.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import ClassVar

from fuggers_py.reference.bonds.types import CalendarId
from fuggers_py.core.calendars import BusinessDayConvention
from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Currency, Date, Frequency
from fuggers_py.core.ids import InstrumentId
from fuggers_py.products.instruments import KindedInstrumentMixin
from fuggers_py.reference.inflation import (
    InflationConvention,
    InflationIndexDefinition,
    USD_CPI_U_NSA,
)

from .common import AccrualPeriod, PayReceive, ScheduleDefinition


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _default_schedule_definition() -> ScheduleDefinition:
    return ScheduleDefinition(
        frequency=Frequency.SEMI_ANNUAL,
        calendar=CalendarId.sifma(),
        business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING,
    )


@dataclass(frozen=True, slots=True)
class StandardCouponInflationSwap(KindedInstrumentMixin):
    """Schedule-driven standard coupon inflation swap.

    ``pay_receive`` is the direction of the fixed leg. The inflation-linked leg
    has the opposite direction and settles the realized CPI change over each
    accrual interval.

    Parameters
    ----------
    trade_date, maturity_date:
        Trade date and final coupon/payment date anchor.
    notional:
        Trade notional in currency units.
    fixed_rate:
        Fixed coupon rate as a raw decimal.
    pay_receive:
        Direction of the fixed leg.
    inflation_convention:
        Inflation index family and lag convention used for the floating leg.
    effective_date:
        Optional effective date. If omitted, a standard settlement lag is
        applied to the trade date.
    currency:
        Contract currency.
    schedule:
        Coupon schedule used for the fixed leg.
    inflation_schedule:
        Optional separate schedule for the inflation leg.
    fixed_day_count_convention:
        Day-count convention for the fixed leg.
    normalize_effective_date_to_reference_month_start:
        Whether the effective date is snapped to the month start used by the
        reference CPI convention.
    fixed_periods_override, inflation_periods_override:
        Optional explicit accrual-period overrides for research or market
        convention control.
    instrument_id:
        Optional stable identifier for the swap.
    """

    KIND: ClassVar[str] = "rates.swap.inflation.standard_coupon"

    trade_date: Date
    maturity_date: Date
    notional: Decimal
    fixed_rate: Decimal
    pay_receive: PayReceive | str = PayReceive.PAY
    inflation_convention: InflationConvention = USD_CPI_U_NSA
    effective_date: Date | None = None
    currency: Currency | str = Currency.USD
    schedule: ScheduleDefinition = field(default_factory=_default_schedule_definition)
    inflation_schedule: ScheduleDefinition | None = None
    fixed_day_count_convention: DayCountConvention | str = DayCountConvention.ACT_365_FIXED
    normalize_effective_date_to_reference_month_start: bool = True
    fixed_periods_override: tuple[AccrualPeriod, ...] = ()
    inflation_periods_override: tuple[AccrualPeriod, ...] = ()
    instrument_id: InstrumentId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "notional", _to_decimal(self.notional))
        object.__setattr__(self, "fixed_rate", _to_decimal(self.fixed_rate))
        object.__setattr__(self, "pay_receive", PayReceive.parse(self.pay_receive))
        if not isinstance(self.currency, Currency):
            object.__setattr__(self, "currency", Currency.from_code(str(self.currency)))
        if not isinstance(self.fixed_day_count_convention, DayCountConvention):
            normalized = str(self.fixed_day_count_convention).strip().upper().replace("/", "_")
            object.__setattr__(self, "fixed_day_count_convention", DayCountConvention[normalized])
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))

        resolved_effective = self.effective_date
        if resolved_effective is None:
            calendar = self.schedule.calendar.to_calendar()
            resolved_effective = calendar.settlement_date(self.trade_date, 2)
        if self.normalize_effective_date_to_reference_month_start:
            resolved_effective = self._normalize_to_reference_month_start(resolved_effective)
        object.__setattr__(self, "effective_date", resolved_effective)
        if self.inflation_schedule is None:
            object.__setattr__(self, "inflation_schedule", self.schedule)
        object.__setattr__(self, "fixed_periods_override", tuple(self.fixed_periods_override))
        object.__setattr__(self, "inflation_periods_override", tuple(self.inflation_periods_override))

        if self.inflation_convention is None:
            raise ValueError("StandardCouponInflationSwap requires an inflation_convention.")
        if self.maturity_date <= self.effective_date:
            raise ValueError("StandardCouponInflationSwap requires maturity_date after effective_date.")
        if self.notional <= Decimal(0):
            raise ValueError("StandardCouponInflationSwap notional must be positive.")
        if self.currency is not self.inflation_convention.currency:
            raise ValueError("StandardCouponInflationSwap currency must match inflation_convention.currency.")
        if self.currency is not Currency.USD or self.inflation_convention.index_source != "CPURNSA":
            raise ValueError("StandardCouponInflationSwap first release supports USD CPI-U / CPURNSA only.")
        if self.schedule.frequency.is_zero() or self.inflation_schedule.frequency.is_zero():
            raise ValueError("StandardCouponInflationSwap requires non-zero coupon frequency.")
        self._validate_periods()

    @classmethod
    def new(
        cls,
        *,
        trade_date: Date,
        maturity_date: Date,
        notional: Decimal,
        fixed_rate: Decimal,
        pay_receive: PayReceive | str = PayReceive.PAY,
        inflation_convention: InflationIndexDefinition = USD_CPI_U_NSA,
        effective_date: Date | None = None,
        currency: Currency | str = Currency.USD,
        schedule: ScheduleDefinition | None = None,
        inflation_schedule: ScheduleDefinition | None = None,
        fixed_day_count_convention: DayCountConvention | str = DayCountConvention.ACT_365_FIXED,
        normalize_effective_date_to_reference_month_start: bool = True,
        fixed_periods: tuple[AccrualPeriod, ...] | None = None,
        inflation_periods: tuple[AccrualPeriod, ...] | None = None,
        instrument_id: InstrumentId | None = None,
    ) -> "StandardCouponInflationSwap":
        """Construct a standard coupon inflation swap."""

        return cls(
            trade_date=trade_date,
            maturity_date=maturity_date,
            notional=notional,
            fixed_rate=fixed_rate,
            pay_receive=pay_receive,
            inflation_convention=inflation_convention,
            effective_date=effective_date,
            currency=currency,
            schedule=_default_schedule_definition() if schedule is None else schedule,
            inflation_schedule=inflation_schedule,
            fixed_day_count_convention=fixed_day_count_convention,
            normalize_effective_date_to_reference_month_start=normalize_effective_date_to_reference_month_start,
            fixed_periods_override=() if fixed_periods is None else tuple(fixed_periods),
            inflation_periods_override=() if inflation_periods is None else tuple(inflation_periods),
            instrument_id=instrument_id,
        )

    def fixed_leg_sign(self) -> Decimal:
        """Return the fixed-leg cash-flow sign."""

        return self.pay_receive.sign()

    def inflation_leg_sign(self) -> Decimal:
        """Return the inflation-leg cash-flow sign."""

        return self.pay_receive.opposite().sign()

    def fixed_periods(self) -> tuple[AccrualPeriod, ...]:
        """Return the fixed-leg coupon periods."""

        if self.fixed_periods_override:
            return self.fixed_periods_override
        return self.schedule.accrual_periods(
            self.effective_date,
            self.maturity_date,
            day_count_convention=self.fixed_day_count_convention,
        )

    def inflation_periods(self) -> tuple[AccrualPeriod, ...]:
        """Return the inflation-leg coupon periods."""

        if self.inflation_periods_override:
            return self.inflation_periods_override
        return self.inflation_schedule.accrual_periods(
            self.effective_date,
            self.maturity_date,
            day_count_convention=DayCountConvention.ACT_365_FIXED,
        )

    def payment_dates(self) -> tuple[Date, ...]:
        """Return the ordered coupon payment dates."""

        return tuple(period.payment_date for period in self.fixed_periods())

    def _normalize_to_reference_month_start(self, date: Date) -> Date:
        calendar = self.schedule.calendar.to_calendar()
        reference_month_start = Date.from_ymd(date.year(), date.month(), 1)
        return calendar.adjust(reference_month_start, BusinessDayConvention.FOLLOWING)

    def _validate_periods(self) -> None:
        fixed_periods = self.fixed_periods()
        inflation_periods = self.inflation_periods()
        if len(fixed_periods) == 0 or len(inflation_periods) == 0:
            raise ValueError("StandardCouponInflationSwap requires at least one coupon period.")
        if len(fixed_periods) != len(inflation_periods):
            raise ValueError("StandardCouponInflationSwap requires matching fixed and inflation schedule lengths.")
        for fixed_period, inflation_period in zip(fixed_periods, inflation_periods, strict=True):
            if fixed_period.start_date >= fixed_period.end_date:
                raise ValueError("StandardCouponInflationSwap fixed schedule contains an invalid accrual period.")
            if inflation_period.start_date >= inflation_period.end_date:
                raise ValueError("StandardCouponInflationSwap inflation schedule contains an invalid accrual period.")
            if (
                fixed_period.start_date != inflation_period.start_date
                or fixed_period.end_date != inflation_period.end_date
                or fixed_period.payment_date != inflation_period.payment_date
            ):
                raise ValueError(
                    "StandardCouponInflationSwap requires aligned fixed and inflation schedules in the first release."
                )
        if fixed_periods[0].start_date != self.effective_date:
            raise ValueError("StandardCouponInflationSwap fixed schedule must start on effective_date.")
        if fixed_periods[-1].end_date != self.maturity_date:
            raise ValueError("StandardCouponInflationSwap fixed schedule must end on maturity_date.")


__all__ = ["StandardCouponInflationSwap"]
