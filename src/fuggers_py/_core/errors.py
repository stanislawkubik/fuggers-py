"""Core exception hierarchy for `fuggers_py`.

These exceptions represent failures in the shared value types, calendars,
day-count logic, and convention types that form the base of the library.
"""

from __future__ import annotations

from dataclasses import dataclass


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


class BondError(FuggersError):
    """Base exception for shared bond and convention failures."""

    @classmethod
    def invalid_spec(cls, reason: str) -> "InvalidBondSpec":
        return InvalidBondSpec(reason=reason)

    @classmethod
    def missing_field(cls, field: str) -> "MissingRequiredField":
        return MissingRequiredField(field=field)

    @classmethod
    def pricing_failed(cls, reason: str) -> "BondPricingError":
        return BondPricingError(reason=reason)


class IdentifierError(BondError):
    """Raised when an instrument identifier is invalid."""


@dataclass(frozen=True, slots=True)
class InvalidIdentifier(IdentifierError):
    """Raised when an identifier fails format or checksum validation."""

    identifier_type: str
    value: str
    reason: str

    def __str__(self) -> str:
        return f"Invalid {self.identifier_type}: {self.value!r} ({self.reason})."


@dataclass(frozen=True, slots=True)
class InvalidBondSpec(BondError):
    """Raised when a bond or convention definition is internally inconsistent."""

    reason: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Invalid bond spec: {self.reason}"


@dataclass(frozen=True, slots=True)
class MissingRequiredField(BondError):
    """Raised when a required field is missing."""

    field: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Missing required field: {self.field}"


@dataclass(frozen=True, slots=True)
class BondPricingError(BondError):
    """Raised when pricing inputs do not admit a valid result."""

    reason: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Bond pricing error: {self.reason}"


@dataclass(frozen=True, slots=True)
class YieldConvergenceFailed(BondError):
    """Raised when a yield solver fails to converge."""

    iterations: int
    residual: float

    def __str__(self) -> str:
        return (
            f"Yield solver failed to converge after {self.iterations} iterations "
            f"(residual={self.residual:.6g})."
        )


@dataclass(frozen=True, slots=True)
class ScheduleError(BondError):
    """Raised when coupon schedule generation fails."""

    reason: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Schedule error: {self.reason}"


@dataclass(frozen=True, slots=True)
class SettlementError(BondError):
    """Raised when settlement-date resolution fails."""

    reason: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Settlement error: {self.reason}"


__all__ = [
    "FuggersError",
    "InvalidDateError",
    "InvalidYieldError",
    "InvalidPriceError",
    "InvalidSpreadError",
    "InvalidCashFlowError",
    "DayCountError",
    "CalendarError",
    "BondError",
    "IdentifierError",
    "InvalidIdentifier",
    "InvalidBondSpec",
    "MissingRequiredField",
    "BondPricingError",
    "YieldConvergenceFailed",
    "ScheduleError",
    "SettlementError",
]
