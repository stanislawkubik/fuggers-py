"""Calibration instruments for rate curves.

The instruments in this module quote raw decimal rates except for futures,
which use price-level quotes. Each instrument resolves a maturity date from a
tenor or explicit date and exposes a par-rate function against a discount
curve.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol

from fuggers_py.products.bonds.cashflows import Schedule, ScheduleConfig
from fuggers_py.reference.bonds.types import CalendarId, StubPeriodRules, Tenor
from fuggers_py.core.calendars import BusinessDayConvention
from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.traits import YieldCurve
from fuggers_py.core.types import Date, Frequency

from ..errors import InvalidCurveInput


def _to_decimal(value: object, *, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _resolve_date(reference_date: Date, tenor: Tenor | None, maturity: Date | None) -> Date:
    if maturity is not None:
        return maturity
    if tenor is None:
        raise InvalidCurveInput("Instrument requires either a tenor or a maturity date.")
    return tenor.add_to(reference_date)


class CalibrationInstrument(Protocol):
    """Protocol for curve-calibration instruments quoted in raw decimals."""

    quote: Decimal

    def maturity_date(self) -> Date:
        """Return the maturity date used to place the calibration pillar."""
        ...

    def par_rate(self, curve: YieldCurve) -> Decimal:
        """Return the model par quote implied by ``curve``."""
        ...


@dataclass(frozen=True, slots=True)
class Deposit:
    """Money-market deposit calibration instrument.

    Quotes are raw decimal money-market rates. The deposit starts on
    ``start_date`` when provided, otherwise on ``reference_date``.
    """

    reference_date: Date
    quote: Decimal
    tenor: Tenor | None = None
    maturity: Date | None = None
    day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED
    start_date: Date | None = None

    _start_date: Date = field(init=False, repr=False)
    _maturity_date: Date = field(init=False, repr=False)

    def __post_init__(self) -> None:
        start = self.start_date or self.reference_date
        maturity = _resolve_date(start, self.tenor, self.maturity)
        if maturity <= start:
            raise InvalidCurveInput("Deposit maturity must be after the start date.")
        object.__setattr__(self, "_start_date", start)
        object.__setattr__(self, "_maturity_date", maturity)
        object.__setattr__(self, "quote", _to_decimal(self.quote, field_name="quote"))

    def maturity_date(self) -> Date:
        """Return the deposit maturity date."""
        return self._maturity_date

    def par_rate(self, curve: YieldCurve) -> Decimal:
        """Return the raw decimal deposit rate implied by the curve."""
        day_count = self.day_count.to_day_count()
        tau = float(day_count.year_fraction(self._start_date, self._maturity_date))
        if tau <= 0.0:
            return Decimal(0)
        df_start = curve.discount_factor(self._start_date)
        df_end = curve.discount_factor(self._maturity_date)
        if df_end == 0:
            raise InvalidCurveInput("Deposit par rate requires non-zero discount factor at maturity.")
        rate = (df_start / df_end - Decimal(1)) / Decimal(str(tau))
        return rate


@dataclass(frozen=True, slots=True)
class Fra:
    """Forward-rate agreement calibration instrument.

    Quotes are raw decimal FRA rates for the accrual window defined by the
    start and end dates.
    """

    reference_date: Date
    quote: Decimal
    start_tenor: Tenor | None = None
    end_tenor: Tenor | None = None
    start_date: Date | None = None
    end_date: Date | None = None
    day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED

    _start_date: Date = field(init=False, repr=False)
    _end_date: Date = field(init=False, repr=False)

    def __post_init__(self) -> None:
        start = self.start_date or _resolve_date(self.reference_date, self.start_tenor, None)
        end = self.end_date or _resolve_date(self.reference_date, self.end_tenor, None)
        if end <= start:
            raise InvalidCurveInput("FRA end date must be after start date.")
        object.__setattr__(self, "_start_date", start)
        object.__setattr__(self, "_end_date", end)
        object.__setattr__(self, "quote", _to_decimal(self.quote, field_name="quote"))

    def maturity_date(self) -> Date:
        """Return the FRA fixing maturity date."""
        return self._end_date

    def par_rate(self, curve: YieldCurve) -> Decimal:
        """Return the raw decimal FRA rate implied by the curve."""
        day_count = self.day_count.to_day_count()
        tau = float(day_count.year_fraction(self._start_date, self._end_date))
        if tau <= 0.0:
            return Decimal(0)
        df_start = curve.discount_factor(self._start_date)
        df_end = curve.discount_factor(self._end_date)
        if df_end == 0:
            raise InvalidCurveInput("FRA par rate requires non-zero discount factor at end date.")
        rate = (df_start / df_end - Decimal(1)) / Decimal(str(tau))
        return rate


@dataclass(frozen=True, slots=True)
class Swap:
    """Fixed-versus-floating swap calibration instrument.

    Quotes are raw decimal fixed rates for the swap's fixed leg.
    """

    reference_date: Date
    quote: Decimal
    tenor: Tenor | None = None
    maturity: Date | None = None
    fixed_frequency: Frequency = Frequency.SEMI_ANNUAL
    fixed_day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED
    calendar: CalendarId = CalendarId.weekend_only()
    business_day_convention: BusinessDayConvention = BusinessDayConvention.MODIFIED_FOLLOWING
    end_of_month: bool = True
    stub_rules: StubPeriodRules = StubPeriodRules.default()
    start_date: Date | None = None

    _start_date: Date = field(init=False, repr=False)
    _maturity_date: Date = field(init=False, repr=False)

    def __post_init__(self) -> None:
        start = self.start_date or self.reference_date
        maturity = _resolve_date(start, self.tenor, self.maturity)
        if maturity <= start:
            raise InvalidCurveInput("Swap maturity must be after the start date.")
        if self.fixed_frequency.is_zero():
            raise InvalidCurveInput("Swap fixed leg frequency must be non-zero.")
        object.__setattr__(self, "_start_date", start)
        object.__setattr__(self, "_maturity_date", maturity)
        object.__setattr__(self, "quote", _to_decimal(self.quote, field_name="quote"))

    def maturity_date(self) -> Date:
        """Return the swap maturity date."""
        return self._maturity_date

    def _fixed_leg_schedule(self) -> Schedule:
        config = ScheduleConfig(
            start_date=self._start_date,
            end_date=self._maturity_date,
            frequency=self.fixed_frequency,
            calendar=self.calendar,
            business_day_convention=self.business_day_convention,
            end_of_month=self.end_of_month,
            stub_rules=self.stub_rules,
        )
        return Schedule.generate(config)

    def par_rate(self, curve: YieldCurve) -> Decimal:
        """Return the raw decimal fixed rate that prices the swap at par."""
        schedule = self._fixed_leg_schedule()
        day_count = self.fixed_day_count.to_day_count()

        df_start = curve.discount_factor(self._start_date)
        df_end = curve.discount_factor(self._maturity_date)
        if df_end == 0:
            raise InvalidCurveInput("Swap par rate requires non-zero discount factor at maturity.")

        annuity = Decimal(0)
        for i in range(1, len(schedule.unadjusted_dates)):
            accrual_start = schedule.unadjusted_dates[i - 1]
            accrual_end = schedule.unadjusted_dates[i]
            tau = day_count.year_fraction(accrual_start, accrual_end)
            pay_date = schedule.dates[i]
            df = curve.discount_factor(pay_date)
            annuity += tau * df

        if annuity == 0:
            raise InvalidCurveInput("Swap par rate requires non-zero fixed leg annuity.")
        par = (df_start - df_end) / annuity
        return par


@dataclass(frozen=True, slots=True)
class Ois:
    """Overnight indexed swap calibration instrument.

    Quotes are raw decimal fixed rates for the OIS fixed leg. The floating leg
    is approximated through the discount-factor change between the start and
    end dates.
    """

    reference_date: Date
    quote: Decimal
    tenor: Tenor | None = None
    maturity: Date | None = None
    fixed_frequency: Frequency = Frequency.SEMI_ANNUAL
    fixed_day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED
    calendar: CalendarId = CalendarId.weekend_only()
    business_day_convention: BusinessDayConvention = BusinessDayConvention.MODIFIED_FOLLOWING
    end_of_month: bool = True
    stub_rules: StubPeriodRules = StubPeriodRules.default()
    start_date: Date | None = None

    _start_date: Date = field(init=False, repr=False)
    _maturity_date: Date = field(init=False, repr=False)

    def __post_init__(self) -> None:
        start = self.start_date or self.reference_date
        maturity = _resolve_date(start, self.tenor, self.maturity)
        if maturity <= start:
            raise InvalidCurveInput("OIS maturity must be after the start date.")
        if self.fixed_frequency.is_zero():
            raise InvalidCurveInput("OIS fixed leg frequency must be non-zero.")
        object.__setattr__(self, "_start_date", start)
        object.__setattr__(self, "_maturity_date", maturity)
        object.__setattr__(self, "quote", _to_decimal(self.quote, field_name="quote"))

    def maturity_date(self) -> Date:
        """Return the OIS maturity date."""
        return self._maturity_date

    def _fixed_leg_schedule(self) -> Schedule:
        config = ScheduleConfig(
            start_date=self._start_date,
            end_date=self._maturity_date,
            frequency=self.fixed_frequency,
            calendar=self.calendar,
            business_day_convention=self.business_day_convention,
            end_of_month=self.end_of_month,
            stub_rules=self.stub_rules,
        )
        return Schedule.generate(config)

    def par_rate(self, curve: YieldCurve) -> Decimal:
        """Return the raw decimal OIS fixed rate implied by the curve.

        The overnight leg is approximated by the discount-factor change
        between start and end dates.
        """

        schedule = self._fixed_leg_schedule()
        day_count = self.fixed_day_count.to_day_count()

        df_start = curve.discount_factor(self._start_date)
        df_end = curve.discount_factor(self._maturity_date)
        if df_end == 0:
            raise InvalidCurveInput("OIS par rate requires non-zero discount factor at maturity.")

        annuity = Decimal(0)
        for i in range(1, len(schedule.unadjusted_dates)):
            accrual_start = schedule.unadjusted_dates[i - 1]
            accrual_end = schedule.unadjusted_dates[i]
            tau = day_count.year_fraction(accrual_start, accrual_end)
            pay_date = schedule.dates[i]
            df = curve.discount_factor(pay_date)
            annuity += tau * df

        if annuity == 0:
            raise InvalidCurveInput("OIS par rate requires non-zero fixed leg annuity.")
        par = (df_start - df_end) / annuity
        return par


@dataclass(frozen=True, slots=True)
class Future:
    """Interest-rate future calibration instrument.

    The market quote is a futures price level. ``quoted_forward_rate`` and
    ``par_rate`` both convert that price into a raw decimal forward rate,
    with ``convexity_adjustment_bps`` applied as a basis-point adjustment.
    """

    reference_date: Date
    quote: Decimal
    start_tenor: Tenor | None = None
    end_tenor: Tenor | None = None
    start_date: Date | None = None
    end_date: Date | None = None
    day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED
    convexity_adjustment_bps: Decimal = Decimal(0)

    _start_date: Date = field(init=False, repr=False)
    _end_date: Date = field(init=False, repr=False)

    def __post_init__(self) -> None:
        start = self.start_date or _resolve_date(self.reference_date, self.start_tenor, None)
        end = self.end_date or _resolve_date(self.reference_date, self.end_tenor, None)
        if end <= start:
            raise InvalidCurveInput("Future end date must be after the start date.")
        object.__setattr__(self, "_start_date", start)
        object.__setattr__(self, "_end_date", end)
        object.__setattr__(self, "quote", _to_decimal(self.quote, field_name="quote"))
        object.__setattr__(
            self,
            "convexity_adjustment_bps",
            _to_decimal(self.convexity_adjustment_bps, field_name="convexity_adjustment_bps"),
        )

    def maturity_date(self) -> Date:
        """Return the future accrual end date."""
        return self._end_date

    def quoted_forward_rate(self) -> Decimal:
        """Convert the futures price quote into a raw decimal forward rate."""
        return (Decimal(100) - self.quote) / Decimal(100)

    def adjusted_forward_rate(self) -> Decimal:
        """Return the quoted forward rate adjusted for convexity in bps."""
        return self.quoted_forward_rate() - self.convexity_adjustment_bps / Decimal(10_000)

    def par_rate(self, curve: YieldCurve) -> Decimal:
        """Return the model forward rate plus convexity adjustment in bps."""
        forward = curve.forward_rate(self._start_date, self._end_date)
        return forward + self.convexity_adjustment_bps / Decimal(10_000)


@dataclass(frozen=True, slots=True)
class BasisSwap:
    """Basis-swap calibration instrument.

    Quotes are raw decimal basis spreads between the receive and pay floating
    legs. ``par_rate`` assumes the same curve on both legs, while
    :meth:`par_basis` can compare two distinct curves.
    """

    reference_date: Date
    quote: Decimal
    tenor: Tenor | None = None
    maturity: Date | None = None
    pay_frequency: Frequency = Frequency.QUARTERLY
    receive_frequency: Frequency = Frequency.QUARTERLY
    day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED
    calendar: CalendarId = CalendarId.weekend_only()
    business_day_convention: BusinessDayConvention = BusinessDayConvention.MODIFIED_FOLLOWING
    end_of_month: bool = True
    stub_rules: StubPeriodRules = StubPeriodRules.default()
    start_date: Date | None = None

    _start_date: Date = field(init=False, repr=False)
    _maturity_date: Date = field(init=False, repr=False)

    def __post_init__(self) -> None:
        start = self.start_date or self.reference_date
        maturity = _resolve_date(start, self.tenor, self.maturity)
        if maturity <= start:
            raise InvalidCurveInput("Basis swap maturity must be after the start date.")
        if self.pay_frequency.is_zero() or self.receive_frequency.is_zero():
            raise InvalidCurveInput("Basis swap frequencies must be non-zero.")
        object.__setattr__(self, "_start_date", start)
        object.__setattr__(self, "_maturity_date", maturity)
        object.__setattr__(self, "quote", _to_decimal(self.quote, field_name="quote"))

    def maturity_date(self) -> Date:
        """Return the basis-swap maturity date."""
        return self._maturity_date

    def par_rate(self, curve: YieldCurve) -> Decimal:
        """Return the par basis spread against a single discount curve."""
        return self.par_basis(curve, curve)

    def par_basis(self, pay_curve: YieldCurve, receive_curve: YieldCurve) -> Decimal:
        """Return the raw decimal basis spread between two curves."""
        receive_leg = self._floating_leg_pv(receive_curve)
        pay_leg = self._floating_leg_pv(pay_curve)
        annuity = self._annuity(pay_curve)
        if annuity == 0:
            raise InvalidCurveInput("Basis swap annuity must be non-zero.")
        return (receive_leg - pay_leg) / annuity

    def _schedule(self, frequency: Frequency) -> Schedule:
        config = ScheduleConfig(
            start_date=self._start_date,
            end_date=self._maturity_date,
            frequency=frequency,
            calendar=self.calendar,
            business_day_convention=self.business_day_convention,
            end_of_month=self.end_of_month,
            stub_rules=self.stub_rules,
        )
        return Schedule.generate(config)

    def _annuity(self, curve: YieldCurve) -> Decimal:
        schedule = self._schedule(self.pay_frequency)
        day_count = self.day_count.to_day_count()
        annuity = Decimal(0)
        for i in range(1, len(schedule.unadjusted_dates)):
            start = schedule.unadjusted_dates[i - 1]
            end = schedule.unadjusted_dates[i]
            pay_date = schedule.dates[i]
            tau = day_count.year_fraction(start, end)
            annuity += tau * curve.discount_factor(pay_date) / curve.discount_factor(self._start_date)
        return annuity

    def _floating_leg_pv(self, curve: YieldCurve) -> Decimal:
        start_df = curve.discount_factor(self._start_date)
        end_df = curve.discount_factor(self._maturity_date)
        return start_df - end_df


@dataclass(frozen=True, slots=True)
class InstrumentSet:
    """Ordered calibration instruments sorted by increasing maturity."""

    instruments: list[CalibrationInstrument]

    def __post_init__(self) -> None:
        if not self.instruments:
            raise InvalidCurveInput("InstrumentSet requires at least one instrument.")

        maturities = [inst.maturity_date() for inst in self.instruments]
        for i in range(1, len(maturities)):
            if maturities[i] < maturities[i - 1]:
                raise InvalidCurveInput("Instruments must be ordered by increasing maturity.")
            if maturities[i] == maturities[i - 1]:
                raise InvalidCurveInput("Duplicate instrument maturities are not allowed.")

    def maturities(self) -> list[Date]:
        """Return the instrument maturity dates in calibration order."""
        return [inst.maturity_date() for inst in self.instruments]


__all__ = [
    "CalibrationInstrument",
    "Deposit",
    "Fra",
    "Future",
    "Ois",
    "Swap",
    "BasisSwap",
    "InstrumentSet",
]
