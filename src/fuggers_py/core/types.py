"""Fundamental value types for fixed-income analytics.

The module defines the core public primitives used across the library:
currency, frequency, compounding, spread classification, date wrappers, price
and yield representations, cash-flow metadata, and cash-flow schedules.
"""

from __future__ import annotations

import calendar as _calendar
import datetime as _dt
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, replace
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, Decimal
from enum import StrEnum

from .errors import (
    InvalidCashFlowError,
    InvalidDateError,
    InvalidPriceError,
    InvalidSpreadError,
    InvalidYieldError,
)
from .traits import Discountable


def _to_decimal(value: object, *, field: str, exc_type: type[Exception]) -> Decimal:
    try:
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, str)):
            return Decimal(value)
        if isinstance(value, float):
            # Avoid binary float artifacts leaking into the public API.
            return Decimal(str(value))
        return Decimal(str(value))
    except Exception as exc:  # pragma: no cover - defensive
        raise exc_type(f"Invalid decimal value for {field}: {value!r}") from exc


class Currency(StrEnum):
    """ISO 4217 currency codes used throughout the library."""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    CAD = "CAD"
    AUD = "AUD"
    NZD = "NZD"
    SEK = "SEK"
    NOK = "NOK"
    DKK = "DKK"
    HKD = "HKD"
    SGD = "SGD"
    CNY = "CNY"
    INR = "INR"
    BRL = "BRL"
    MXN = "MXN"
    ZAR = "ZAR"

    def code(self) -> str:
        """Return the ISO alphabetic currency code."""

        return self.value

    def symbol(self) -> str:
        """Return a commonly used currency symbol."""

        return {
            Currency.USD: "$",
            Currency.EUR: "€",
            Currency.GBP: "£",
            Currency.JPY: "¥",
            Currency.CHF: "CHF",
            Currency.CAD: "C$",
            Currency.AUD: "A$",
            Currency.NZD: "NZ$",
            Currency.SEK: "kr",
            Currency.NOK: "kr",
            Currency.DKK: "kr",
            Currency.HKD: "HK$",
            Currency.SGD: "S$",
            Currency.CNY: "¥",
            Currency.INR: "₹",
            Currency.BRL: "R$",
            Currency.MXN: "Mex$",
            Currency.ZAR: "R",
        }[self]

    def name(self) -> str:  # type: ignore[override]
        """Return the display name of the currency."""

        return {
            Currency.USD: "US Dollar",
            Currency.EUR: "Euro",
            Currency.GBP: "British Pound",
            Currency.JPY: "Japanese Yen",
            Currency.CHF: "Swiss Franc",
            Currency.CAD: "Canadian Dollar",
            Currency.AUD: "Australian Dollar",
            Currency.NZD: "New Zealand Dollar",
            Currency.SEK: "Swedish Krona",
            Currency.NOK: "Norwegian Krone",
            Currency.DKK: "Danish Krone",
            Currency.HKD: "Hong Kong Dollar",
            Currency.SGD: "Singapore Dollar",
            Currency.CNY: "Chinese Yuan",
            Currency.INR: "Indian Rupee",
            Currency.BRL: "Brazilian Real",
            Currency.MXN: "Mexican Peso",
            Currency.ZAR: "South African Rand",
        }[self]

    def numeric_code(self) -> int:
        """Return the ISO 4217 numeric code."""

        return {
            Currency.USD: 840,
            Currency.EUR: 978,
            Currency.GBP: 826,
            Currency.JPY: 392,
            Currency.CHF: 756,
            Currency.CAD: 124,
            Currency.AUD: 36,
            Currency.NZD: 554,
            Currency.SEK: 752,
            Currency.NOK: 578,
            Currency.DKK: 208,
            Currency.HKD: 344,
            Currency.SGD: 702,
            Currency.CNY: 156,
            Currency.INR: 356,
            Currency.BRL: 986,
            Currency.MXN: 484,
            Currency.ZAR: 710,
        }[self]

    def is_g10(self) -> bool:
        """Return True for the common "G10" FX set."""

        return self in {
            Currency.USD,
            Currency.EUR,
            Currency.GBP,
            Currency.JPY,
            Currency.CHF,
            Currency.CAD,
            Currency.AUD,
            Currency.NZD,
            Currency.SEK,
            Currency.NOK,
        }

    def is_emerging(self) -> bool:
        """Return True for a simple EM classification."""

        return self in {Currency.CNY, Currency.INR, Currency.BRL, Currency.MXN, Currency.ZAR}

    def decimal_places(self) -> int:
        """Return the typical number of decimal places for amounts in this currency."""

        return 0 if self is Currency.JPY else 2

    def standard_settlement_days(self) -> int:
        """Return a standard spot-settlement lag for the currency."""

        return 1 if self in {Currency.USD, Currency.GBP} else 2

    @classmethod
    def from_code(cls, code: str) -> Currency:
        """Parse an ISO currency code (case-insensitive)."""

        if not isinstance(code, str):
            raise ValueError("Currency.from_code expects a string.")
        key = code.strip().upper()
        try:
            return cls(key)
        except ValueError as exc:
            raise ValueError(f"Invalid currency code: {code!r}") from exc

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.code()


class Frequency(StrEnum):
    """Coupon or payment frequency."""

    ANNUAL = "ANNUAL"
    SEMI_ANNUAL = "SEMI_ANNUAL"
    QUARTERLY = "QUARTERLY"
    MONTHLY = "MONTHLY"
    ZERO = "ZERO"

    def periods_per_year(self) -> int:
        """Return the number of periods per year."""

        return {
            Frequency.ANNUAL: 1,
            Frequency.SEMI_ANNUAL: 2,
            Frequency.QUARTERLY: 4,
            Frequency.MONTHLY: 12,
            Frequency.ZERO: 0,
        }[self]

    def months_per_period(self) -> int:
        """Return the number of calendar months per period."""

        return {
            Frequency.ANNUAL: 12,
            Frequency.SEMI_ANNUAL: 6,
            Frequency.QUARTERLY: 3,
            Frequency.MONTHLY: 1,
            Frequency.ZERO: 0,
        }[self]

    def is_zero(self) -> bool:
        """Return True for the zero-coupon frequency."""

        return self is Frequency.ZERO

    def __str__(self) -> str:  # pragma: no cover - trivial
        return {
            Frequency.ANNUAL: "Annual",
            Frequency.SEMI_ANNUAL: "Semi-Annual",
            Frequency.QUARTERLY: "Quarterly",
            Frequency.MONTHLY: "Monthly",
            Frequency.ZERO: "Zero Coupon",
        }[self]


class Compounding(StrEnum):
    """Interest-rate compounding convention."""

    SIMPLE = "SIMPLE"
    ANNUAL = "ANNUAL"
    SEMI_ANNUAL = "SEMI_ANNUAL"
    QUARTERLY = "QUARTERLY"
    MONTHLY = "MONTHLY"
    DAILY = "DAILY"
    CONTINUOUS = "CONTINUOUS"

    def periods_per_year(self) -> int:
        """Return periods per year, using a sentinel for continuous compounding."""

        return {
            Compounding.SIMPLE: 0,
            Compounding.ANNUAL: 1,
            Compounding.SEMI_ANNUAL: 2,
            Compounding.QUARTERLY: 4,
            Compounding.MONTHLY: 12,
            Compounding.DAILY: 365,
            Compounding.CONTINUOUS: 2**32 - 1,  # sentinel for continuous compounding
        }[self]

    def is_continuous(self) -> bool:
        """Return True for continuous compounding."""

        return self is Compounding.CONTINUOUS

    def is_simple(self) -> bool:
        """Return True for simple compounding."""

        return self is Compounding.SIMPLE

    def __str__(self) -> str:  # pragma: no cover - trivial
        return {
            Compounding.SIMPLE: "Simple",
            Compounding.ANNUAL: "Annual",
            Compounding.SEMI_ANNUAL: "Semi-Annual",
            Compounding.QUARTERLY: "Quarterly",
            Compounding.MONTHLY: "Monthly",
            Compounding.DAILY: "Daily",
            Compounding.CONTINUOUS: "Continuous",
        }[self]


class SpreadType(StrEnum):
    """Quoted spread family used by pricing and analytics APIs."""

    Z_SPREAD = "Z_SPREAD"
    G_SPREAD = "G_SPREAD"
    I_SPREAD = "I_SPREAD"
    ASSET_SWAP_PAR = "ASSET_SWAP_PAR"
    ASSET_SWAP_PROCEEDS = "ASSET_SWAP_PROCEEDS"
    OAS = "OAS"
    CREDIT = "CREDIT"
    DISCOUNT_MARGIN = "DISCOUNT_MARGIN"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name.replace("_", " ").title()


class CashFlowType(StrEnum):
    """Categorize a cash flow by its economic role."""

    COUPON = "COUPON"
    PRINCIPAL = "PRINCIPAL"
    COUPON_AND_PRINCIPAL = "COUPON_AND_PRINCIPAL"
    PARTIAL_PRINCIPAL = "PARTIAL_PRINCIPAL"
    FLOATING_COUPON = "FLOATING_COUPON"
    INFLATION_COUPON = "INFLATION_COUPON"
    INFLATION_PRINCIPAL = "INFLATION_PRINCIPAL"
    SINKING_FUND = "SINKING_FUND"
    CALL = "CALL"
    PUT = "PUT"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name.replace("_", " ").title()


@dataclass(frozen=True, order=True)
class Date:
    """An immutable wrapper around `datetime.date`.

    `Date` preserves the ordering and calendar arithmetic of the underlying
    `datetime.date` without attaching timezone, holiday, or business-day
    metadata. Weekend-only helpers are available on the type itself; calendar
    aware business-day logic lives in :mod:`fuggers_py.core.calendars`.

    Attributes
    ----------
    _date
        The underlying naive `datetime.date`.
    """

    _date: _dt.date

    @classmethod
    def from_ymd(cls, year: int, month: int, day: int) -> Date:
        """Construct a `Date` from year, month, and day components."""

        try:
            return cls(_dt.date(int(year), int(month), int(day)))
        except Exception as exc:
            raise InvalidDateError(f"Invalid date components: {year=}, {month=}, {day=}.") from exc

    @classmethod
    def parse(cls, text: str) -> Date:
        """Parse an ISO date string (`YYYY-MM-DD`)."""

        if not isinstance(text, str):
            raise InvalidDateError("Date.parse expects a string in ISO format 'YYYY-MM-DD'.")
        try:
            return cls(_dt.date.fromisoformat(text.strip()))
        except Exception as exc:
            raise InvalidDateError(f"Invalid ISO date string: {text!r}.") from exc

    @classmethod
    def today(cls) -> Date:
        """Return today's date in the local timezone."""

        return cls(_dt.date.today())

    def year(self) -> int:
        """Return the year."""

        return self._date.year

    def month(self) -> int:
        """Return the month (1-12)."""

        return self._date.month

    def day(self) -> int:
        """Return the day of month (1-31)."""

        return self._date.day

    def day_of_year(self) -> int:
        """Return the day-of-year (1-366)."""

        return self._date.timetuple().tm_yday

    def weekday(self) -> int:
        """Return the weekday as an integer where Monday=0 and Sunday=6."""

        return self._date.weekday()

    def as_naive_date(self) -> _dt.date:
        """Return the underlying `datetime.date`."""

        return self._date

    def is_leap_year(self) -> bool:
        """Return True if the year is a leap year."""

        return _calendar.isleap(self.year())

    def days_in_month(self) -> int:
        """Return the number of days in this date's month."""

        return _calendar.monthrange(self.year(), self.month())[1]

    def days_in_year(self) -> int:
        """Return the number of days in this date's year (365 or 366)."""

        return 366 if self.is_leap_year() else 365

    def start_of_month(self) -> Date:
        """Return the first day of the month."""

        return Date.from_ymd(self.year(), self.month(), 1)

    def end_of_month(self) -> Date:
        """Return the last day of the month."""

        return Date.from_ymd(self.year(), self.month(), self.days_in_month())

    def start_of_year(self) -> Date:
        """Return January 1st of this date's year."""

        return Date.from_ymd(self.year(), 1, 1)

    def end_of_year(self) -> Date:
        """Return December 31st of this date's year."""

        return Date.from_ymd(self.year(), 12, 31)

    def is_end_of_month(self) -> bool:
        """Return True if this date is the last day of its month."""

        return self.day() == self.days_in_month()

    def is_weekend(self) -> bool:
        """Return True for Saturday/Sunday."""

        return self.weekday() in (5, 6)

    def is_weekday(self) -> bool:
        """Return True for Monday-Friday."""

        return not self.is_weekend()

    def add_days(self, n: int) -> Date:
        """Add `n` calendar days."""

        try:
            return Date(self._date + _dt.timedelta(days=int(n)))
        except Exception as exc:
            raise InvalidDateError(f"Date.add_days produced an invalid date: {self} + {n} days.") from exc

    def add_months(self, n: int) -> Date:
        """Add `n` calendar months, clamping invalid day-of-month to month-end."""

        month_index = self.year() * 12 + (self.month() - 1) + int(n)
        year = month_index // 12
        month = month_index % 12 + 1
        if year < 1 or year > 9999:
            raise InvalidDateError(f"Date.add_months out of supported range: {self} + {n} months.")
        day = min(self.day(), _calendar.monthrange(year, month)[1])
        return Date.from_ymd(year, month, day)

    def add_years(self, n: int) -> Date:
        """Add `n` calendar years, clamping invalid day-of-month to month-end."""

        year = self.year() + int(n)
        if year < 1 or year > 9999:
            raise InvalidDateError(f"Date.add_years out of supported range: {self} + {n} years.")
        day = min(self.day(), _calendar.monthrange(year, self.month())[1])
        return Date.from_ymd(year, self.month(), day)

    def days_between(self, other: Date) -> int:
        """Return the signed day count from this date to `other`.

        The start date is excluded and the end date is included.
        """

        return (other._date - self._date).days

    def next_weekday(self) -> Date:
        """Return the next weekday, leaving weekdays unchanged."""

        wd = self.weekday()
        if wd == 5:  # Saturday
            return self.add_days(2)
        if wd == 6:  # Sunday
            return self.add_days(1)
        return self

    def prev_weekday(self) -> Date:
        """Return the previous weekday, leaving weekdays unchanged."""

        wd = self.weekday()
        if wd == 5:  # Saturday
            return self.add_days(-1)
        if wd == 6:  # Sunday
            return self.add_days(-2)
        return self

    def add_business_days(self, n: int) -> Date:
        """Add business days using weekend-only logic (no holiday calendar)."""

        days = int(n)
        if days == 0:
            return self

        step = 1 if days > 0 else -1
        remaining = abs(days)
        current = self
        while remaining > 0:
            current = current.add_days(step)
            if current.is_weekday():
                remaining -= 1
        return current

    def business_days_between(self, other: Date) -> int:
        """Count business days between dates.

        The start date is excluded and the end date is included. Uses
        weekend-only logic with no holiday calendar.
        """

        if self == other:
            return 0
        if self < other:
            count = 0
            current = self
            while current < other:
                current = current.add_days(1)
                if current.is_weekday():
                    count += 1
            return count
        return -other.business_days_between(self)

    @staticmethod
    def min(a: Date, b: Date) -> Date:
        """Return the earlier date."""

        return a if a <= b else b

    @staticmethod
    def max(a: Date, b: Date) -> Date:
        """Return the later date."""

        return a if a >= b else b

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self._date.isoformat()

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"Date({self})"


@dataclass(frozen=True)
class Price:
    """A percentage-of-par price quoted in a currency.

    The stored numeric value is in percent-of-par terms, so ``98.50`` means
    98.50% of par and ``1.00`` means 1.00% of par, not a decimal price.

    Attributes
    ----------
    _percentage
        Price quoted as a percentage of par.
    _currency
        Currency denomination of the quote.
    """

    _percentage: Decimal
    _currency: Currency

    @classmethod
    def new(cls, percentage: object, currency: Currency) -> Price:
        """Create a price from a percentage-of-par value."""

        pct = _to_decimal(percentage, field="Price.percentage", exc_type=InvalidPriceError)
        inst = cls(pct, currency)
        inst.validate()
        return inst

    @classmethod
    def from_decimal(cls, decimal_value: object, currency: Currency) -> Price:
        """Create a price from a decimal-of-par value.

        Parameters
        ----------
        decimal_value
            Raw decimal price where ``1.0`` means par and ``0.985`` means
            98.5% of par.
        currency
            Denomination of the price.
        """

        dec = _to_decimal(decimal_value, field="Price.decimal", exc_type=InvalidPriceError)
        return cls.new(dec * Decimal(100), currency)

    def validate(self) -> None:
        """Validate the price, which must be strictly positive."""

        if self._percentage <= 0:
            raise InvalidPriceError(f"Price must be positive, got {self._percentage}.")

    def as_percentage(self) -> Decimal:
        """Return the percentage-of-par value."""

        return self._percentage

    def as_decimal(self) -> Decimal:
        """Return the decimal-of-par value."""

        return self._percentage / Decimal(100)

    def currency(self) -> Currency:
        """Return the currency denomination."""

        return self._currency

    def is_at_par(self) -> bool:
        """Return True if the price is exactly at par (100%)."""

        return self._percentage == Decimal(100)

    def is_discount(self) -> bool:
        """Return True if the price is below par."""

        return self._percentage < Decimal(100)

    def is_premium(self) -> bool:
        """Return True if the price is above par."""

        return self._percentage > Decimal(100)

    @classmethod
    def par(cls, currency: Currency) -> Price:
        """Return a par price (100%)."""

        return cls.new(Decimal(100), currency)

    def discount_or_premium(self) -> Decimal:
        """Return the signed difference from par in percentage points."""

        return self._percentage - Decimal(100)

    def to_dirty(self, accrued: object) -> Price:
        """Convert a clean price to a dirty price.

        Parameters
        ----------
        accrued
            Accrued interest in percentage-of-par points, not raw currency
            units.
        """

        acc = _to_decimal(accrued, field="accrued", exc_type=InvalidPriceError)
        return Price.new(self._percentage + acc, self._currency)

    def to_clean(self, accrued: object) -> Price:
        """Convert a dirty price to a clean price.

        Parameters
        ----------
        accrued
            Accrued interest in percentage-of-par points, not raw currency
            units.
        """

        acc = _to_decimal(accrued, field="accrued", exc_type=InvalidPriceError)
        return Price.new(self._percentage - acc, self._currency)

    def dollar_value(self, face_value: object) -> Decimal:
        """Return the currency value given a face amount in currency units."""

        fv = _to_decimal(face_value, field="face_value", exc_type=InvalidPriceError)
        return self.as_decimal() * fv

    def round(self, decimal_places: int) -> Price:
        """Round the percentage to `decimal_places` decimal places."""

        dp = int(decimal_places)
        quant = Decimal(1).scaleb(-dp)
        return Price.new(self._percentage.quantize(quant, rounding=ROUND_HALF_EVEN), self._currency)

    def same_currency(self, other: Price) -> bool:
        """Return True if two prices are denominated in the same currency."""

        return self._currency == other._currency

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self._percentage}% {self._currency.code()}"


@dataclass(frozen=True)
class Yield:
    """An annualized yield rate with an explicit compounding convention.

    The stored value is a raw decimal rate. For example, ``0.05`` means 5%,
    ``5.0`` is a percentage value, and ``500`` basis points is 5%.

    Attributes
    ----------
    _value
        Yield as a raw decimal rate.
    _compounding
        Compounding convention used to interpret the rate.
    """

    _value: Decimal
    _compounding: Compounding

    @classmethod
    def new(cls, value: object, compounding: Compounding) -> Yield:
        """Create a yield from a raw decimal rate."""

        val = _to_decimal(value, field="Yield.value", exc_type=InvalidYieldError)
        inst = cls(val, compounding)
        inst.validate()
        return inst

    @classmethod
    def from_percentage(cls, percentage: object, compounding: Compounding) -> Yield:
        """Create a yield from a quoted percentage rate."""

        pct = _to_decimal(percentage, field="Yield.percentage", exc_type=InvalidYieldError)
        return cls.new(pct / Decimal(100), compounding)

    @classmethod
    def from_bps(cls, bps: object, compounding: Compounding) -> Yield:
        """Create a yield from basis points."""

        b = _to_decimal(bps, field="Yield.bps", exc_type=InvalidYieldError)
        return cls.new(b / Decimal(10_000), compounding)

    def validate(self) -> None:
        """Validate the yield is within a conservative domain of [-100%, +100%]."""

        if self._value < Decimal("-1") or self._value > Decimal("1"):
            raise InvalidYieldError(
                f"Yield must be between -100% and +100% (as decimal -1..1), got {self._value}."
            )

    def value(self) -> Decimal:
        """Return the yield as a decimal rate."""

        return self._value

    def as_percentage(self) -> Decimal:
        """Return the yield as a percentage."""

        return self._value * Decimal(100)

    def as_bps(self) -> int:
        """Return the yield in basis points, truncated toward zero."""

        bps = self._value * Decimal(10_000)
        return int(bps.to_integral_value(rounding=ROUND_DOWN))

    def compounding(self) -> Compounding:
        """Return the compounding convention."""

        return self._compounding

    def convert_to(self, target_compounding: Compounding) -> Yield:
        """Convert this yield to `target_compounding` preserving annual growth.

        Conversion preserves the 1-year accumulation factor:

        - SIMPLE:        A = 1 + r
        - CONTINUOUS:    A = exp(r)
        - n-periodic:    A = (1 + r/n)^n

        The target rate is solved from the same accumulation factor.
        """

        if target_compounding == self._compounding:
            return self

        r = self._value
        one = Decimal(1)

        if self._compounding.is_simple():
            factor = one + r
        elif self._compounding.is_continuous():
            factor = r.exp()
        else:
            n = Decimal(self._compounding.periods_per_year())
            factor = (one + r / n) ** n

        if factor <= 0:
            raise InvalidYieldError(f"Cannot convert yield with non-positive accumulation factor: {factor}.")

        if target_compounding.is_simple():
            target_r = factor - one
        elif target_compounding.is_continuous():
            target_r = factor.ln()
        else:
            n = Decimal(target_compounding.periods_per_year())
            target_r = n * (factor ** (one / n) - one)

        return Yield(target_r, target_compounding)

    def __str__(self) -> str:  # pragma: no cover - trivial
        pct = self.as_percentage()
        return f"{pct}% ({self._compounding})"


@dataclass(frozen=True)
class Spread:
    """A spread quoted in basis points with a spread type.

    The stored value is basis points, so ``125`` means 125 bps, or 1.25%
    in percentage terms.

    Attributes
    ----------
    _bps
        Spread amount in basis points.
    _spread_type
        Spread family or quoting convention.
    """

    _bps: Decimal
    _spread_type: SpreadType

    @classmethod
    def new(cls, bps: object, spread_type: SpreadType) -> Spread:
        """Create a spread from a basis-point value."""

        b = _to_decimal(bps, field="Spread.bps", exc_type=InvalidSpreadError)
        return cls(b, spread_type)

    @classmethod
    def from_decimal(cls, decimal_value: object, spread_type: SpreadType) -> Spread:
        """Create a spread from a decimal spread quote."""

        dec = _to_decimal(decimal_value, field="Spread.decimal", exc_type=InvalidSpreadError)
        return cls.new(dec * Decimal(10_000), spread_type)

    @classmethod
    def from_bps_i32(cls, value: int, spread_type: SpreadType) -> Spread:
        """Create a spread from an integer basis-point value."""

        return cls.new(int(value), spread_type)

    def as_bps(self) -> Decimal:
        """Return the spread in basis points."""

        return self._bps

    def as_decimal(self) -> Decimal:
        """Return the spread as a decimal."""

        return self._bps / Decimal(10_000)

    def as_percentage(self) -> Decimal:
        """Return the spread as a percentage."""

        return self._bps / Decimal(100)

    def spread_type(self) -> SpreadType:
        """Return the spread type."""

        return self._spread_type

    def is_positive(self) -> bool:
        """Return True if the spread is strictly positive."""

        return self._bps > 0

    def is_negative(self) -> bool:
        """Return True if the spread is strictly negative."""

        return self._bps < 0

    def is_zero(self) -> bool:
        """Return True if the spread is exactly zero."""

        return self._bps == 0

    def abs(self) -> Spread:
        """Return the absolute value of the spread."""

        return Spread.new(abs(self._bps), self._spread_type)

    def round(self, decimal_places: int) -> Spread:
        """Round the basis-point value to `decimal_places` decimal places."""

        dp = int(decimal_places)
        quant = Decimal(1).scaleb(-dp)
        return Spread.new(self._bps.quantize(quant, rounding=ROUND_HALF_EVEN), self._spread_type)

    def same_type(self, other: Spread) -> bool:
        """Return True if two spreads have the same `SpreadType`."""

        return self._spread_type == other._spread_type

    def _assert_same_type(self, other: Spread) -> None:
        if not self.same_type(other):
            raise InvalidSpreadError(
                f"Spread type mismatch: {self._spread_type.name} vs {other._spread_type.name}."
            )

    def __add__(self, other: object) -> Spread:
        if not isinstance(other, Spread):
            return NotImplemented
        self._assert_same_type(other)
        return Spread.new(self._bps + other._bps, self._spread_type)

    def __sub__(self, other: object) -> Spread:
        if not isinstance(other, Spread):
            return NotImplemented
        self._assert_same_type(other)
        return Spread.new(self._bps - other._bps, self._spread_type)

    def __neg__(self) -> Spread:
        return Spread.new(-self._bps, self._spread_type)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self._bps} bps ({self._spread_type})"


@dataclass(frozen=True)
class CashFlow(Discountable):
    """A dated cash flow with optional accrual and reference metadata.

    Amounts are stored in currency units, not as percentages. Coupon-like cash
    flows may carry accrual dates, a floating reference rate, and remaining
    notional after principal amortization.

    Attributes
    ----------
    _date
        Payment date.
    _amount
        Cash amount in currency units.
    _cf_type
        Economic classification of the cash flow.
    _accrual_start, _accrual_end
        Optional accrual period bounds.
    _reference_rate
        Optional floating reference rate.
    _notional_after
        Optional remaining notional after the payment.
    """

    _date: Date
    _amount: Decimal
    _cf_type: CashFlowType
    _accrual_start: Date | None = None
    _accrual_end: Date | None = None
    _reference_rate: Decimal | None = None
    _notional_after: Decimal | None = None

    @classmethod
    def new(cls, date: Date, amount: object, cf_type: CashFlowType) -> CashFlow:
        """Create a cash flow with a payment date, amount, and type."""

        amt = _to_decimal(amount, field="CashFlow.amount", exc_type=InvalidCashFlowError)
        return cls(date, amt, cf_type)

    @classmethod
    def coupon(cls, date: Date, amount: object) -> CashFlow:
        """Create a fixed coupon cash flow."""

        return cls.new(date, amount, CashFlowType.COUPON)

    @classmethod
    def coupon_with_accrual(
        cls, date: Date, amount: object, accrual_start: Date, accrual_end: Date
    ) -> CashFlow:
        """Create a fixed coupon with accrual start and end metadata."""

        cf = cls.coupon(date, amount)
        return cf.with_accrual(accrual_start, accrual_end)

    @classmethod
    def floating_coupon(cls, date: Date, amount: object, reference_rate: object | None = None) -> CashFlow:
        """Create a floating coupon cash flow."""

        cf = cls.new(date, amount, CashFlowType.FLOATING_COUPON)
        if reference_rate is not None:
            cf = cf.with_reference_rate(reference_rate)
        return cf

    @classmethod
    def principal(cls, date: Date, amount: object) -> CashFlow:
        """Create a principal cash flow."""

        return cls.new(date, amount, CashFlowType.PRINCIPAL)

    @classmethod
    def partial_principal(cls, date: Date, amount: object, notional_after: object | None = None) -> CashFlow:
        """Create a partial principal payment."""

        cf = cls.new(date, amount, CashFlowType.PARTIAL_PRINCIPAL)
        if notional_after is not None:
            cf = cf.with_notional_after(notional_after)
        return cf

    @classmethod
    def final_payment(cls, date: Date, coupon_amount: object, principal_amount: object) -> CashFlow:
        """Create a final coupon-plus-principal cash flow."""

        c = _to_decimal(coupon_amount, field="CashFlow.coupon_amount", exc_type=InvalidCashFlowError)
        p = _to_decimal(principal_amount, field="CashFlow.principal_amount", exc_type=InvalidCashFlowError)
        return cls.new(date, c + p, CashFlowType.COUPON_AND_PRINCIPAL).with_notional_after(Decimal(0))

    @classmethod
    def final_payment_with_accrual(
        cls,
        date: Date,
        coupon_amount: object,
        principal_amount: object,
        accrual_start: Date,
        accrual_end: Date,
    ) -> CashFlow:
        """Create a final payment with accrual metadata."""

        return cls.final_payment(date, coupon_amount, principal_amount).with_accrual(accrual_start, accrual_end)

    @classmethod
    def inflation_coupon(cls, date: Date, amount: object) -> CashFlow:
        """Create an inflation-linked coupon cash flow."""

        return cls.new(date, amount, CashFlowType.INFLATION_COUPON)

    @classmethod
    def inflation_principal(cls, date: Date, amount: object) -> CashFlow:
        """Create an inflation-linked principal cash flow."""

        return cls.new(date, amount, CashFlowType.INFLATION_PRINCIPAL)

    def date(self) -> Date:
        """Return the cash-flow payment date."""

        return self._date

    def payment_date(self) -> Date:
        """Return the payment date (alias for `date()`)."""

        return self._date

    def amount(self) -> Decimal:
        """Return the cash-flow amount in currency units."""

        return self._amount

    def cf_type(self) -> CashFlowType:
        """Return the cash-flow type."""

        return self._cf_type

    def accrual_start(self) -> Date | None:
        """Return the accrual start date if available."""

        return self._accrual_start

    def accrual_end(self) -> Date | None:
        """Return the accrual end date if available."""

        return self._accrual_end

    def reference_rate(self) -> Decimal | None:
        """Return the floating reference rate if available."""

        return self._reference_rate

    def notional_after(self) -> Decimal | None:
        """Return the remaining notional after this cash flow, if available."""

        return self._notional_after

    def is_coupon(self) -> bool:
        """Return True for cash flows that contain coupon interest."""

        return self._cf_type in {
            CashFlowType.COUPON,
            CashFlowType.FLOATING_COUPON,
            CashFlowType.INFLATION_COUPON,
            CashFlowType.COUPON_AND_PRINCIPAL,
        }

    def is_principal(self) -> bool:
        """Return True for cash flows that contain principal."""

        return self._cf_type in {
            CashFlowType.PRINCIPAL,
            CashFlowType.PARTIAL_PRINCIPAL,
            CashFlowType.INFLATION_PRINCIPAL,
            CashFlowType.COUPON_AND_PRINCIPAL,
        }

    def is_floating(self) -> bool:
        """Return True for floating-rate coupons."""

        return self._cf_type is CashFlowType.FLOATING_COUPON

    def is_inflation_linked(self) -> bool:
        """Return True for inflation-linked cash flows."""

        return self._cf_type in {CashFlowType.INFLATION_COUPON, CashFlowType.INFLATION_PRINCIPAL}

    def with_accrual(self, accrual_start: Date, accrual_end: Date) -> CashFlow:
        """Return a copy with accrual metadata set.

        The accrual start must not be after the accrual end.
        """

        if accrual_start > accrual_end:
            raise InvalidCashFlowError(f"Accrual start {accrual_start} must be <= accrual end {accrual_end}.")
        return replace(self, _accrual_start=accrual_start, _accrual_end=accrual_end)

    def with_reference_rate(self, rate: object) -> CashFlow:
        """Return a copy with the floating reference rate set."""

        rr = _to_decimal(rate, field="CashFlow.reference_rate", exc_type=InvalidCashFlowError)
        return replace(self, _reference_rate=rr)

    def with_notional_after(self, amount: object) -> CashFlow:
        """Return a copy with the remaining notional set."""

        na = _to_decimal(amount, field="CashFlow.notional_after", exc_type=InvalidCashFlowError)
        return replace(self, _notional_after=na)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"CashFlow({self._date}, {self._amount}, {self._cf_type.name})"


class CashFlowSchedule:
    """An ordered, mutable container for cash flows.

    The schedule preserves insertion order, can be sorted in place by payment
    date, and exposes an immutable tuple view for callers that should not
    mutate the underlying list.

    Attributes
    ----------
    _cashflows
        Backing list of cash flows in insertion order.
    """

    def __init__(self, cashflows: Iterable[CashFlow] | None = None) -> None:
        self._cashflows: list[CashFlow] = list(cashflows) if cashflows is not None else []

    @classmethod
    def new(cls) -> CashFlowSchedule:
        """Create an empty schedule."""

        return cls()

    @classmethod
    def with_capacity(cls, capacity: int) -> CashFlowSchedule:
        """Create an empty schedule with a capacity hint (no-op in Python)."""

        _ = int(capacity)
        return cls()

    def push(self, cf: CashFlow) -> None:
        """Append a cash flow."""

        self._cashflows.append(cf)

    def as_slice(self) -> Sequence[CashFlow]:
        """Return an immutable view of the cash flows."""

        return tuple(self._cashflows)

    def len(self) -> int:
        """Return the number of cash flows."""

        return len(self._cashflows)

    def is_empty(self) -> bool:
        """Return True if the schedule is empty."""

        return not self._cashflows

    def iter(self) -> Iterator[CashFlow]:
        """Return an iterator over cash flows."""

        return iter(self._cashflows)

    def total(self) -> Decimal:
        """Return the sum of all cash-flow amounts in currency units."""

        total = Decimal(0)
        for cf in self._cashflows:
            total += cf.amount()
        return total

    def sort_by_date(self) -> CashFlowSchedule:
        """Sort cash flows in place by payment date."""

        self._cashflows.sort(key=lambda cf: cf.date().as_naive_date())
        return self

    def after(self, date: Date) -> CashFlowSchedule:
        """Return a new schedule containing cash flows strictly after `date`."""

        return CashFlowSchedule(cf for cf in self._cashflows if cf.date() > date)

    def __iter__(self) -> Iterator[CashFlow]:
        return iter(self._cashflows)

    def __len__(self) -> int:
        return len(self._cashflows)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"CashFlowSchedule(len={len(self._cashflows)})"
