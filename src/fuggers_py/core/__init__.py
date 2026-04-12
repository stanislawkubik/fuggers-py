"""Shared primitives for the fixed-income library.

`fuggers_py.core` is the foundation layer for the public API. It exposes the
typed dates, prices, yields, spreads, identifiers, calendars, day-count
conventions, and protocol interfaces that higher-level analytics build on.

Public imports are intended to work from this module directly, for example::

    from fuggers_py.core import Date, Price, SIFMACalendar, Act360
"""

from __future__ import annotations

from .calendars import (
    BusinessDayConvention,
    Calendar,
    CalendarData,
    CustomCalendarBuilder,
    DynamicCalendar,
    HolidayBitmap,
    HolidayCalendarBuilder,
    JapanCalendar,
    JointCalendar,
    SIFMACalendar,
    Target2Calendar,
    UKCalendar,
    USCalendar,
    USGovernmentCalendar,
    WeekendCalendar,
    WeekendType,
    easter_sunday,
    last_weekday_of_month,
    nth_weekday_of_month,
    observed_date,
)
from .daycounts import (
    Act360,
    Act365,
    Act365Fixed,
    Act365Leap,
    ActActAfb,
    ActActIcma,
    ActActIsda,
    DayCount,
    DayCountConvention,
    Thirty360,
    Thirty360E,
    Thirty360EIsda,
    Thirty360German,
    Thirty360US,
)
from .errors import *  # noqa: F403
from .errors import FuggersError
from .ids import (
    CurrencyPair,
    CurveId,
    EtfId,
    InstrumentId,
    PortfolioId,
    VolSurfaceId,
    YearMonth,
)
from .traits import (
    Discountable,
    PricingEngine,
    RiskCalculator,
    SpreadCalculator,
)
from .types import (
    CashFlow,
    CashFlowSchedule,
    CashFlowType,
    Compounding,
    Currency,
    Date,
    Frequency,
    Price,
    Spread,
    SpreadType,
    Yield,
)

__all__ = [
    "FuggersError",
    # Primary types most users import
    "Date",
    "Currency",
    "Frequency",
    "Compounding",
    "Price",
    "Yield",
    "Spread",
    "SpreadType",
    "CashFlowType",
    "CashFlow",
    "CashFlowSchedule",
    "CurrencyPair",
    "CurveId",
    "EtfId",
    "InstrumentId",
    "PortfolioId",
    "VolSurfaceId",
    "YearMonth",
    # Daycounts
    "DayCount",
    "DayCountConvention",
    "Act360",
    "Act365Fixed",
    "Act365Leap",
    "ActActAfb",
    "ActActIcma",
    "ActActIsda",
    "Thirty360E",
    "Thirty360EIsda",
    "Thirty360German",
    "Thirty360US",
    "Act365",
    "Thirty360",
    # Calendars
    "BusinessDayConvention",
    "WeekendType",
    "Calendar",
    "WeekendCalendar",
    "USCalendar",
    "SIFMACalendar",
    "USGovernmentCalendar",
    "Target2Calendar",
    "UKCalendar",
    "JapanCalendar",
    "JointCalendar",
    "HolidayBitmap",
    "HolidayCalendarBuilder",
    "CalendarData",
    "DynamicCalendar",
    "CustomCalendarBuilder",
    # Calendar helpers
    "easter_sunday",
    "last_weekday_of_month",
    "nth_weekday_of_month",
    "observed_date",
    # Traits
    "PricingEngine",
    "RiskCalculator",
    "Discountable",
    "SpreadCalculator",
]
