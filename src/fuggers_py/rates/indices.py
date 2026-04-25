"""Rates-domain fixing, index, and overnight conventions."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Iterable, Mapping, Sequence

from fuggers_py._core.calendars import Calendar, WeekendCalendar
from fuggers_py._core.daycounts import DayCountConvention
from fuggers_py._core.types import Currency, Date

if TYPE_CHECKING:
    from fuggers_py.curves import YieldCurve


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class ArrearConvention(str, Enum):
    """Coupon reset timing relative to the accrual period."""

    IN_ADVANCE = "IN_ADVANCE"
    IN_ARREARS = "IN_ARREARS"


class ObservationShiftType(str, Enum):
    """Observation-date adjustment applied to overnight fixings."""

    NONE = "NONE"
    LOOKBACK = "LOOKBACK"
    OBSERVATION_SHIFT = "OBSERVATION_SHIFT"


ShiftType = ObservationShiftType


@dataclass(frozen=True, slots=True)
class LookbackDays:
    """Business-day lookback applied to overnight observations."""

    days: int = 0

    def __int__(self) -> int:
        return self.days


@dataclass(frozen=True, slots=True)
class LockoutDays:
    """Final business days that reuse an earlier overnight fixing."""

    days: int = 0

    def __int__(self) -> int:
        return self.days


class OvernightCompounding(str, Enum):
    """Overnight coupon aggregation method for floating-rate instruments."""

    COMPOUNDED = "COMPOUNDED"
    SIMPLE = "SIMPLE"
    AVERAGED = "AVERAGED"

    def compounded_rate(
        self,
        start_date: Date,
        end_date: Date,
        *,
        index_name: str,
        fixing_store: "IndexFixingStore",
        conventions: "IndexConventions",
        calendar: Calendar | None = None,
        fallback_rate: Decimal | None = None,
        forward_curve: object | None = None,
        as_of: Date | None = None,
    ) -> Decimal:
        """Return the compounded overnight rate over an accrual window."""

        active_calendar = calendar or WeekendCalendar()
        schedule = _business_accrual_schedule(start_date, end_date, active_calendar)
        if not schedule:
            return Decimal(0)

        compound = Decimal(1)
        for index, (fixing_date, segment_end) in enumerate(schedule):
            observed = _observed_schedule_date(schedule, index, conventions, active_calendar)
            rate = _lookup_or_project_rate(
                index_name=index_name,
                fixing_store=fixing_store,
                observed_date=observed,
                segment_start=fixing_date,
                segment_end=segment_end,
                fallback_rate=fallback_rate,
                forward_curve=forward_curve,
                as_of=as_of,
            )
            compound *= overnight_factor(rate, fixing_date, segment_end, conventions)

        total_accrual = self.accrual_factor(start_date, end_date, conventions=conventions)
        if total_accrual == 0:
            return Decimal(0)
        return (compound - Decimal(1)) / total_accrual

    def simple_average_rate(
        self,
        start_date: Date,
        end_date: Date,
        *,
        index_name: str,
        fixing_store: "IndexFixingStore",
        conventions: "IndexConventions",
        calendar: Calendar | None = None,
        fallback_rate: Decimal | None = None,
        forward_curve: object | None = None,
        as_of: Date | None = None,
    ) -> Decimal:
        """Return the simple weighted-average overnight rate over a period."""

        active_calendar = calendar or WeekendCalendar()
        schedule = _business_accrual_schedule(start_date, end_date, active_calendar)
        if not schedule:
            return Decimal(0)

        weighted = Decimal(0)
        total = Decimal(0)
        for index, (fixing_date, segment_end) in enumerate(schedule):
            observed = _observed_schedule_date(schedule, index, conventions, active_calendar)
            rate = _lookup_or_project_rate(
                index_name=index_name,
                fixing_store=fixing_store,
                observed_date=observed,
                segment_start=fixing_date,
                segment_end=segment_end,
                fallback_rate=fallback_rate,
                forward_curve=forward_curve,
                as_of=as_of,
            )
            accrual = conventions.day_count.to_day_count().year_fraction(fixing_date, segment_end)
            weighted += rate * accrual
            total += accrual
        if total == 0:
            return Decimal(0)
        return weighted / total

    def required_fixing_dates(
        self,
        start_date: Date,
        end_date: Date,
        *,
        conventions: "IndexConventions",
        calendar: Calendar | None = None,
    ) -> list[Date]:
        """Return the fixing dates needed to value the accrual window."""

        active_calendar = calendar or WeekendCalendar()
        schedule = _business_accrual_schedule(start_date, end_date, active_calendar)
        return [
            _observed_schedule_date(schedule, index, conventions, active_calendar)
            for index, _ in enumerate(schedule)
        ]

    def accrual_factor(self, start_date: Date, end_date: Date, *, conventions: "IndexConventions") -> Decimal:
        """Return the accrual year fraction for the coupon window."""

        if end_date <= start_date:
            return Decimal(0)
        return conventions.day_count.to_day_count().year_fraction(start_date, end_date)


class PublicationTime(str, Enum):
    """Publication timing for daily overnight fixings."""

    SAME_DAY = "SAME_DAY"
    END_OF_DAY = "END_OF_DAY"
    NEXT_BUSINESS_DAY = "NEXT_BUSINESS_DAY"


@dataclass(frozen=True, slots=True)
class IndexConventions:
    """Conventions for floating-rate and overnight reference indices."""

    day_count: DayCountConvention = DayCountConvention.ACT_360
    arrear_convention: ArrearConvention = ArrearConvention.IN_ARREARS
    overnight_compounding: OvernightCompounding | None = None
    publication_time: PublicationTime | None = None
    publication_lag_days: int = 0
    shift_type: ObservationShiftType = ObservationShiftType.NONE
    lookback_days: int = 0
    lockout_days: int = 0
    rate_cutoff_days: int = 0

    def __post_init__(self) -> None:
        if self.overnight_compounding is None:
            object.__setattr__(self, "overnight_compounding", OvernightCompounding.COMPOUNDED)
        if self.publication_time is None:
            object.__setattr__(self, "publication_time", PublicationTime.SAME_DAY)

    @property
    def observation_shift_type(self) -> ObservationShiftType:
        """Return the configured observation-shift mode."""

        return self.shift_type

    @property
    def observation_shift_days(self) -> int:
        """Return the effective observation shift in business days."""

        if self.shift_type is ObservationShiftType.OBSERVATION_SHIFT:
            return self.lookback_days
        return 0


def _business_accrual_schedule(start_date: Date, end_date: Date, calendar: Calendar) -> list[tuple[Date, Date]]:
    if end_date <= start_date:
        return []
    current = calendar.next_business_day(start_date)
    schedule: list[tuple[Date, Date]] = []
    while current < end_date:
        next_business = calendar.add_business_days(current, 1)
        segment_end = Date.min(next_business, end_date)
        schedule.append((current, segment_end))
        current = next_business
    return schedule


def observation_date(date: Date, conventions: IndexConventions, calendar: Calendar | None = None) -> Date:
    """Return the observed fixing date used for an overnight accrual date."""

    active_calendar = calendar or WeekendCalendar()
    if conventions.observation_shift_type in {ObservationShiftType.LOOKBACK, ObservationShiftType.OBSERVATION_SHIFT}:
        shifted = active_calendar.add_business_days(date, -int(conventions.lookback_days))
        return active_calendar.previous_business_day(shifted)
    return active_calendar.previous_business_day(date)


def _observed_schedule_date(
    schedule: list[tuple[Date, Date]],
    index: int,
    conventions: IndexConventions,
    calendar: Calendar,
) -> Date:
    lockout_days = max(int(conventions.lockout_days or conventions.rate_cutoff_days), 0)
    cutoff_index = index
    if lockout_days > 0 and index >= len(schedule) - lockout_days:
        cutoff_index = max(len(schedule) - lockout_days - 1, 0)
    fixing_date, _ = schedule[cutoff_index]
    return observation_date(fixing_date, conventions, calendar=calendar)


def publication_date(date: Date, conventions: IndexConventions, calendar: Calendar | None = None) -> Date:
    """Return the publication date for a fixing observed on ``date``."""

    active_calendar = calendar or WeekendCalendar()
    return active_calendar.add_business_days(date, int(conventions.publication_lag_days))


def overnight_factor(rate: Decimal, start: Date, end: Date, conventions: IndexConventions) -> Decimal:
    """Return the gross overnight accrual factor for one sub-period."""

    year_fraction = conventions.day_count.to_day_count().year_fraction(start, end)
    return Decimal(1) + rate * year_fraction


def _lookup_or_project_rate(
    *,
    index_name: str,
    fixing_store: "IndexFixingStore",
    observed_date: Date,
    segment_start: Date,
    segment_end: Date,
    fallback_rate: Decimal | None,
    forward_curve: object | None,
    as_of: Date | None,
) -> Decimal:
    if as_of is None or observed_date <= as_of:
        fixing = fixing_store.get_rate(index_name, observed_date)
        if fixing is not None:
            return fixing

    if forward_curve is not None:
        if hasattr(forward_curve, "forward_rate"):
            return _to_decimal(forward_curve.forward_rate(segment_start, segment_end))
        if hasattr(forward_curve, "forward_rate_at") and hasattr(forward_curve, "reference_date"):
            reference_date = getattr(forward_curve, "reference_date")
            tenor = max(reference_date.days_between(segment_start), 0) / 365.0
            return _to_decimal(forward_curve.forward_rate_at(tenor))
        if hasattr(forward_curve, "forward_rate_between") and hasattr(forward_curve, "reference_date"):
            reference_date = getattr(forward_curve, "reference_date")
            start_tenor = max(reference_date.days_between(segment_start), 0) / 365.0
            end_tenor = max(reference_date.days_between(segment_end), 0) / 365.0
            return _to_decimal(forward_curve.forward_rate_between(start_tenor, end_tenor))

    if fallback_rate is not None:
        return fallback_rate

    fixing = fixing_store.get_rate(index_name, observed_date)
    if fixing is not None:
        return fixing
    raise KeyError(f"Missing fixing for {index_name} on {observed_date}.")


class IndexSource(str, Enum):
    """Origin of an index fixing used in coupon calculations."""

    MANUAL = "MANUAL"
    PUBLICATION = "PUBLICATION"
    CURVE = "CURVE"
    FALLBACK = "FALLBACK"


@dataclass(frozen=True, slots=True)
class IndexFixing:
    """Stored fixing for a reference index on a specific fixing date."""

    index_name: str
    fixing_date: Date
    rate: Decimal
    publication_date: Date | None = None
    source: IndexSource = IndexSource.MANUAL

    def __post_init__(self) -> None:
        object.__setattr__(self, "index_name", self.index_name.strip().upper())
        object.__setattr__(self, "rate", _to_decimal(self.rate))


@dataclass(slots=True)
class IndexFixingStore:
    """In-memory storage for historical reference-index fixings."""

    _fixings: dict[str, dict[Date, IndexFixing]] = field(default_factory=dict)

    @staticmethod
    def _normalize_index_name(index_name: str) -> str:
        return index_name.strip().upper()

    @classmethod
    def from_rates(
        cls,
        index_name: str,
        mapping_or_sequence: Mapping[Date, object] | Sequence[tuple[Date, object]],
    ) -> "IndexFixingStore":
        """Build a store from raw date-to-rate pairs for one index."""

        store = cls()
        items = mapping_or_sequence.items() if isinstance(mapping_or_sequence, Mapping) else mapping_or_sequence
        for fixing_date, rate in items:
            store.add_fixing(index_name, fixing_date, rate)
        return store

    def add_fixing(
        self,
        index_name: str,
        fixing_date: Date,
        rate: object,
        *,
        publication_date: Date | None = None,
        source: IndexSource = IndexSource.MANUAL,
    ) -> "IndexFixingStore":
        """Insert or overwrite a single fixing."""

        name = self._normalize_index_name(index_name)
        fixing = IndexFixing(
            index_name=name,
            fixing_date=fixing_date,
            rate=_to_decimal(rate),
            publication_date=publication_date,
            source=source,
        )
        self._fixings.setdefault(name, {})[fixing_date] = fixing
        return self

    def add_fixings(self, fixings: Iterable[IndexFixing]) -> "IndexFixingStore":
        """Insert multiple fixings."""

        for fixing in fixings:
            self.add_fixing(
                fixing.index_name,
                fixing.fixing_date,
                fixing.rate,
                publication_date=fixing.publication_date,
                source=fixing.source,
            )
        return self

    def get_fixing(self, index_name: str, fixing_date: Date) -> IndexFixing | None:
        """Return the fixing record for ``index_name`` and ``fixing_date``."""

        return self._fixings.get(self._normalize_index_name(index_name), {}).get(fixing_date)

    def get_rate(self, index_name: str, fixing_date: Date) -> Decimal | None:
        """Return the raw fixing rate for ``index_name`` and ``fixing_date``."""

        fixing = self.get_fixing(index_name, fixing_date)
        return None if fixing is None else fixing.rate

    def has_fixing(self, index_name: str, fixing_date: Date) -> bool:
        return self.get_fixing(index_name, fixing_date) is not None

    def history(self, index_name: str, *, start: Date | None = None, end: Date | None = None) -> list[IndexFixing]:
        """Return stored fixings for ``index_name`` ordered by fixing date."""

        series = list(self._fixings.get(self._normalize_index_name(index_name), {}).values())
        series.sort(key=lambda fixing: fixing.fixing_date)
        if start is not None:
            series = [fixing for fixing in series if fixing.fixing_date >= start]
        if end is not None:
            series = [fixing for fixing in series if fixing.fixing_date <= end]
        return series

    def get_range(self, index_name: str, start_date: Date, end_date: Date) -> list[IndexFixing]:
        """Return fixings between ``start_date`` and ``end_date`` inclusive."""

        return self.history(index_name, start=start_date, end=end_date)

    def last_fixing_before(self, index_name: str, date: Date) -> IndexFixing | None:
        """Return the latest stored fixing strictly before ``date``."""

        history = self.history(index_name, end=date.add_days(-1))
        return None if not history else history[-1]

    def indices(self) -> tuple[str, ...]:
        """Return normalized index names held by the store."""

        return tuple(sorted(self._fixings))

    def count(self, index: str | None = None) -> int:
        """Return the number of stored fixings, optionally for one index."""

        if index is None:
            return sum(len(series) for series in self._fixings.values())
        return len(self._fixings.get(self._normalize_index_name(index), {}))

    def has_index(self, index_name: str) -> bool:
        """Return whether the store contains any fixings for ``index_name``."""

        return self._normalize_index_name(index_name) in self._fixings

    def clear(self) -> None:
        """Remove all stored fixings."""

        self._fixings.clear()

    def rate_for_period(
        self,
        index_name: str,
        start_date: Date,
        end_date: Date,
        *,
        conventions: IndexConventions,
        fallback_rate: Decimal | None = None,
        calendar: Calendar | None = None,
        forward_curve: YieldCurve | object | None = None,
        as_of: Date | None = None,
    ) -> Decimal:
        """Compute the period rate implied by stored overnight fixings."""

        if end_date <= start_date:
            return Decimal(0)
        active_calendar = calendar or WeekendCalendar()
        compounding = conventions.overnight_compounding or OvernightCompounding.COMPOUNDED
        if compounding is OvernightCompounding.COMPOUNDED:
            return compounding.compounded_rate(
                start_date,
                end_date,
                index_name=index_name,
                fixing_store=self,
                conventions=conventions,
                calendar=active_calendar,
                fallback_rate=fallback_rate,
                forward_curve=forward_curve,
                as_of=as_of,
            )
        return compounding.simple_average_rate(
            start_date,
            end_date,
            index_name=index_name,
            fixing_store=self,
            conventions=conventions,
            calendar=active_calendar,
            fallback_rate=fallback_rate,
            forward_curve=forward_curve,
            as_of=as_of,
        )


@dataclass(frozen=True, slots=True)
class BondIndex:
    """Reference-rate definition backed by an optional fixing store."""

    name: str
    rate_index: object | None = None
    currency: Currency | None = None
    source: IndexSource = IndexSource.MANUAL
    conventions: IndexConventions = field(default_factory=IndexConventions)
    fixing_store: IndexFixingStore | None = None

    def fixing(self, fixing_date: Date, *, store: IndexFixingStore | None = None) -> Decimal | None:
        """Return the stored fixing for ``fixing_date`` when available."""

        active_store = store or self.fixing_store
        if active_store is None:
            return None
        return active_store.get_rate(self.name, fixing_date)

    def rate_for_period(
        self,
        start_date: Date,
        end_date: Date,
        *,
        store: IndexFixingStore | None = None,
        fallback_rate: Decimal | None = None,
        forward_curve: YieldCurve | object | None = None,
        as_of: Date | None = None,
    ) -> Decimal:
        """Return the rate applied to an accrual period."""

        active_store = store or self.fixing_store
        if active_store is None:
            if fallback_rate is None:
                raise KeyError(f"No fixing store configured for index {self.name}.")
            return fallback_rate
        return active_store.rate_for_period(
            self.name,
            start_date,
            end_date,
            conventions=self.conventions,
            fallback_rate=fallback_rate,
            calendar=None,
            forward_curve=forward_curve,
            as_of=as_of,
        )

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


__all__ = [
    "ArrearConvention",
    "BondIndex",
    "IndexConventions",
    "IndexFixing",
    "IndexFixingStore",
    "IndexSource",
    "LockoutDays",
    "LookbackDays",
    "ObservationShiftType",
    "OvernightCompounding",
    "PublicationTime",
    "ShiftType",
    "observation_date",
    "overnight_factor",
    "publication_date",
]
