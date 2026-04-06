"""Core exception hierarchy for `fuggers_py`.

These exceptions represent failures in the shared value types, calendars,
day-count logic, and trait interfaces that form the base of the library.
"""

from __future__ import annotations


class FuggersError(Exception):
    """Base exception for all `fuggers_py` domain errors."""


class InvalidDateError(FuggersError):
    """Raised when a `Date` cannot be constructed, parsed, or adjusted."""


class InvalidYieldError(FuggersError):
    """Raised when a `Yield` is invalid or outside supported bounds."""


class InvalidPriceError(FuggersError):
    """Raised when a `Price` is invalid, such as when it is non-positive."""


class InvalidSpreadError(FuggersError):
    """Raised when a `Spread` is invalid or used with an incompatible type."""


class InvalidCashFlowError(FuggersError):
    """Raised when a `CashFlow` is invalid or missing required metadata."""


class DayCountError(FuggersError):
    """Raised when a day-count calculation fails or is not well-defined."""


class CalendarError(FuggersError):
    """Raised when a calendar operation fails or receives invalid inputs."""


__all__ = [
    "FuggersError",
    "InvalidDateError",
    "InvalidYieldError",
    "InvalidPriceError",
    "InvalidSpreadError",
    "InvalidCashFlowError",
    "DayCountError",
    "CalendarError",
]
