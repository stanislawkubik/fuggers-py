"""Day-count conventions.

All year-fraction methods in this module use raw decimal outputs. Intervals are
interpreted as start-exclusive and end-inclusive, and negative intervals are
supported by negating the result.
"""

from __future__ import annotations

import datetime as _dt
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from .errors import DayCountError
from .types import Date, Frequency


def _normalize_interval(start: Date, end: Date) -> tuple[int, Date, Date]:
    if start <= end:
        return 1, start, end
    return -1, end, start


def _includes_feb29(start: Date, end: Date) -> bool:
    """Return True if (start, end] includes a Feb 29."""

    start_ord = start.as_naive_date().toordinal()
    end_ord = end.as_naive_date().toordinal()
    for year in range(start.year(), end.year() + 1):
        try:
            feb29 = _dt.date(year, 2, 29)
        except ValueError:
            continue
        if start_ord < feb29.toordinal() <= end_ord:
            return True
    return False


def _is_last_day_of_feb(d: Date) -> bool:
    return d.month() == 2 and d.day() == d.days_in_month()


class DayCount(ABC):
    """Abstract day-count convention interface.

    Implementations return raw decimal year fractions and integer day counts.
    The fraction is not a percentage quote and should be used directly in
    accrual calculations.
    """

    @abstractmethod
    def name(self) -> str:
        """Return the convention name in its market-standard form."""

    @abstractmethod
    def year_fraction(self, start: Date, end: Date) -> Decimal:
        """Return the raw decimal year fraction between two dates."""

    @abstractmethod
    def day_count(self, start: Date, end: Date) -> int:
        """Return the signed day count between two dates."""


class Act360(DayCount):
    """ACT/360 day-count convention."""

    def name(self) -> str:
        return "ACT/360"

    def day_count(self, start: Date, end: Date) -> int:
        return start.days_between(end)

    def year_fraction(self, start: Date, end: Date) -> Decimal:
        return Decimal(self.day_count(start, end)) / Decimal(360)


class Act365Fixed(DayCount):
    """ACT/365F day-count convention."""

    def name(self) -> str:
        return "ACT/365F"

    def day_count(self, start: Date, end: Date) -> int:
        return start.days_between(end)

    def year_fraction(self, start: Date, end: Date) -> Decimal:
        return Decimal(self.day_count(start, end)) / Decimal(365)


class Act365Leap(DayCount):
    """ACT/365L day-count convention.

    Uses a 366-day denominator when the accrual interval contains 29 February
    and 365 otherwise.
    """

    def name(self) -> str:
        return "ACT/365L"

    def day_count(self, start: Date, end: Date) -> int:
        return start.days_between(end)

    def year_fraction(self, start: Date, end: Date) -> Decimal:
        sign, s, e = _normalize_interval(start, end)
        denom = Decimal(366 if _includes_feb29(s, e) else 365)
        return Decimal(sign) * (Decimal(s.days_between(e)) / denom)


class ActActIsda(DayCount):
    """ACT/ACT ISDA day-count convention."""

    def name(self) -> str:
        return "ACT/ACT ISDA"

    def day_count(self, start: Date, end: Date) -> int:
        return start.days_between(end)

    def year_fraction(self, start: Date, end: Date) -> Decimal:
        sign, s, e = _normalize_interval(start, end)
        if s == e:
            return Decimal(0)

        start_ord = s.as_naive_date().toordinal()
        end_ord = e.as_naive_date().toordinal()

        total = Decimal(0)
        for year in range(s.year(), e.year() + 1):
            year_start_ord = _dt.date(year, 1, 1).toordinal()
            year_end_ord = _dt.date(year, 12, 31).toordinal()

            lo = max(start_ord + 1, year_start_ord)
            hi = min(end_ord, year_end_ord)
            if hi < lo:
                continue

            days_in_period = hi - lo + 1
            days_in_year = 366 if _dt.date(year, 12, 31).toordinal() - _dt.date(year, 1, 1).toordinal() + 1 == 366 else 365
            total += Decimal(days_in_period) / Decimal(days_in_year)

        return Decimal(sign) * total


class ActActAfb(DayCount):
    """ACT/ACT AFB day-count convention.

    Uses a whole-years-plus-remaining-days approach. The remaining-day
    denominator is 366 if the residual period contains 29 February and 365
    otherwise.
    """

    def name(self) -> str:
        return "ACT/ACT AFB"

    def day_count(self, start: Date, end: Date) -> int:
        return start.days_between(end)

    def year_fraction(self, start: Date, end: Date) -> Decimal:
        sign, s, e = _normalize_interval(start, end)
        if s == e:
            return Decimal(0)

        whole_years = 0
        cursor = s
        while True:
            nxt = cursor.add_years(1)
            if nxt <= e:
                whole_years += 1
                cursor = nxt
            else:
                break

        remaining_days = cursor.days_between(e)
        denom = Decimal(366 if _includes_feb29(cursor, e) else 365)
        return Decimal(sign) * (Decimal(whole_years) + Decimal(remaining_days) / denom)


@dataclass(frozen=True)
class ActActIcma(DayCount):
    """ACT/ACT ICMA with an explicit coupon frequency.

    The convention depends on the coupon schedule frequency and on the exact
    coupon period boundaries used for the accrual calculation.
    """

    _frequency: Frequency

    @classmethod
    def new(cls, frequency: Frequency) -> ActActIcma:
        """Create an ICMA day-count with the given coupon frequency."""

        if frequency.is_zero():
            raise DayCountError("ACT/ACT ICMA requires a non-zero frequency.")
        return cls(frequency)

    @classmethod
    def annual(cls) -> ActActIcma:
        """Create an ICMA convention with annual coupon frequency."""

        return cls.new(Frequency.ANNUAL)

    @classmethod
    def semi_annual(cls) -> ActActIcma:
        """Create an ICMA convention with semi-annual coupon frequency."""

        return cls.new(Frequency.SEMI_ANNUAL)

    @classmethod
    def quarterly(cls) -> ActActIcma:
        """Create an ICMA convention with quarterly coupon frequency."""

        return cls.new(Frequency.QUARTERLY)

    @classmethod
    def monthly(cls) -> ActActIcma:
        """Create an ICMA convention with monthly coupon frequency."""

        return cls.new(Frequency.MONTHLY)

    def frequency(self) -> Frequency:
        """Return the coupon frequency used by the convention."""

        return self._frequency

    def name(self) -> str:
        return "ACT/ACT ICMA"

    def day_count(self, start: Date, end: Date) -> int:
        return start.days_between(end)

    def accrued_days(self, accrual_start: Date, accrual_end: Date) -> int:
        """Return accrued days between the accrual dates."""

        return self.day_count(accrual_start, accrual_end)

    def year_fraction_with_period(
        self, accrual_start: Date, accrual_end: Date, period_start: Date, period_end: Date
    ) -> Decimal:
        """Return the year fraction using explicit coupon period boundaries.

        The coupon period is used to normalize the accrual when the accrual
        window does not match the full coupon schedule period.
        """

        sign, a_s, a_e = _normalize_interval(accrual_start, accrual_end)
        if period_start >= period_end:
            raise DayCountError("ICMA requires period_start < period_end.")

        accrued = a_s.days_between(a_e)
        period_days = period_start.days_between(period_end)
        if period_days == 0:
            raise DayCountError("ICMA requires a non-zero coupon period length.")

        freq = self._frequency.periods_per_year()
        if freq <= 0:
            raise DayCountError("ICMA requires a non-zero frequency.")

        return Decimal(sign) * (Decimal(accrued) / (Decimal(period_days) * Decimal(freq)))

    def year_fraction(self, start: Date, end: Date) -> Decimal:
        """Return the year fraction using the accrual window as the coupon period."""

        return self.year_fraction_with_period(start, end, start, end)


class Thirty360E(DayCount):
    """30E/360 day-count convention (Eurobond basis)."""

    def name(self) -> str:
        return "30E/360"

    def day_count(self, start: Date, end: Date) -> int:
        sign, s, e = _normalize_interval(start, end)
        d1 = min(s.day(), 30)
        d2 = min(e.day(), 30)
        days = 360 * (e.year() - s.year()) + 30 * (e.month() - s.month()) + (d2 - d1)
        return sign * days

    def year_fraction(self, start: Date, end: Date) -> Decimal:
        return Decimal(self.day_count(start, end)) / Decimal(360)


class Thirty360EIsda(DayCount):
    """30E/360 ISDA day-count convention with end-of-month adjustment."""

    def name(self) -> str:
        return "30E/360 ISDA"

    def day_count(self, start: Date, end: Date) -> int:
        sign, s, e = _normalize_interval(start, end)

        d1 = 30 if s.is_end_of_month() else min(s.day(), 30)
        d2 = 30 if e.is_end_of_month() else min(e.day(), 30)
        days = 360 * (e.year() - s.year()) + 30 * (e.month() - s.month()) + (d2 - d1)
        return sign * days

    def year_fraction(self, start: Date, end: Date) -> Decimal:
        return Decimal(self.day_count(start, end)) / Decimal(360)


class Thirty360German(DayCount):
    """30/360 German day-count convention.

    Also known as 30/360 ISDA in some market references.
    """

    def name(self) -> str:
        return "30/360 German"

    def day_count(self, start: Date, end: Date) -> int:
        sign, s, e = _normalize_interval(start, end)

        d1 = 30 if s.day() == 31 or _is_last_day_of_feb(s) else s.day()
        d2 = 30 if e.day() == 31 or _is_last_day_of_feb(e) else e.day()
        days = 360 * (e.year() - s.year()) + 30 * (e.month() - s.month()) + (d2 - d1)
        return sign * days

    def year_fraction(self, start: Date, end: Date) -> Decimal:
        return Decimal(self.day_count(start, end)) / Decimal(360)


class Thirty360US(DayCount):
    """30/360 US day-count convention.

    Also known as Bond Basis. The implementation includes end-of-February
    handling consistent with common market practice.
    """

    def name(self) -> str:
        return "30/360 US"

    def day_count(self, start: Date, end: Date) -> int:
        sign, s, e = _normalize_interval(start, end)

        y1, m1, d1 = s.year(), s.month(), s.day()
        y2, m2, d2 = e.year(), e.month(), e.day()

        # Bloomberg-style February EOM rules:
        if _is_last_day_of_feb(s):
            d1 = 30
        if _is_last_day_of_feb(e) and d1 == 30:
            d2 = 30

        if d1 == 31:
            d1 = 30
        if d2 == 31 and d1 == 30:
            d2 = 30

        days = 360 * (y2 - y1) + 30 * (m2 - m1) + (d2 - d1)
        return sign * days

    def year_fraction(self, start: Date, end: Date) -> Decimal:
        return Decimal(self.day_count(start, end)) / Decimal(360)


class DayCountConvention(StrEnum):
    """Closed vocabulary of supported day-count conventions."""

    ACT_360 = "ACT_360"
    ACT_365_FIXED = "ACT_365_FIXED"
    ACT_365_LEAP = "ACT_365_LEAP"
    ACT_ACT_AFB = "ACT_ACT_AFB"
    ACT_ACT_ICMA = "ACT_ACT_ICMA"
    ACT_ACT_ISDA = "ACT_ACT_ISDA"
    THIRTY_360_E = "THIRTY_360_E"
    THIRTY_360_E_ISDA = "THIRTY_360_E_ISDA"
    THIRTY_360_GERMAN = "THIRTY_360_GERMAN"
    THIRTY_360_US = "THIRTY_360_US"

    @classmethod
    def all(cls) -> list[DayCountConvention]:
        """Return all supported conventions."""

        return list(cls)

    def __str__(self) -> str:  # pragma: no cover - legacy public behavior
        return f"{self.__class__.__name__}.{self._name_}"

    def name(self) -> str:  # type: ignore[override]
        """Return the convention name in market-standard form."""

        return {
            DayCountConvention.ACT_360: Act360().name(),
            DayCountConvention.ACT_365_FIXED: Act365Fixed().name(),
            DayCountConvention.ACT_365_LEAP: Act365Leap().name(),
            DayCountConvention.ACT_ACT_AFB: ActActAfb().name(),
            DayCountConvention.ACT_ACT_ICMA: ActActIcma.semi_annual().name(),
            DayCountConvention.ACT_ACT_ISDA: ActActIsda().name(),
            DayCountConvention.THIRTY_360_E: Thirty360E().name(),
            DayCountConvention.THIRTY_360_E_ISDA: Thirty360EIsda().name(),
            DayCountConvention.THIRTY_360_GERMAN: Thirty360German().name(),
            DayCountConvention.THIRTY_360_US: Thirty360US().name(),
        }[self]

    def to_day_count(self) -> DayCount:
        """Construct the day-count object for this convention."""

        return {
            DayCountConvention.ACT_360: Act360(),
            DayCountConvention.ACT_365_FIXED: Act365Fixed(),
            DayCountConvention.ACT_365_LEAP: Act365Leap(),
            DayCountConvention.ACT_ACT_AFB: ActActAfb(),
            DayCountConvention.ACT_ACT_ICMA: ActActIcma.semi_annual(),
            DayCountConvention.ACT_ACT_ISDA: ActActIsda(),
            DayCountConvention.THIRTY_360_E: Thirty360E(),
            DayCountConvention.THIRTY_360_E_ISDA: Thirty360EIsda(),
            DayCountConvention.THIRTY_360_GERMAN: Thirty360German(),
            DayCountConvention.THIRTY_360_US: Thirty360US(),
        }[self]


# Aliases required by the spec.
Act365 = Act365Fixed
Thirty360 = Thirty360US
