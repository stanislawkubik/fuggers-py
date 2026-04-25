"""Internal shared primitives for the fixed-income library.

`fuggers_py._core` owns the shared dates, prices, yields, spreads,
identifiers, calendars, day-count conventions, and small protocols that the
rest of the library builds on.
"""

from __future__ import annotations

from .calendar_id import CalendarId
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
from .option_type import OptionType
from .pay_receive import PayReceive
from .reference import ReferenceData, ResolvableReference
from .settlement_rules import SettlementAdjustment
from .tenor import Tenor
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
from .yield_calculation_rules import YieldCalculationRules

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
    "Tenor",
    "CalendarId",
    "SettlementAdjustment",
    "YieldCalculationRules",
    "PayReceive",
    "OptionType",
    "ReferenceData",
    "ResolvableReference",
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
