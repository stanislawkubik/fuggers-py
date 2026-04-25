"""Inflation-domain exception hierarchy."""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py._core import YearMonth
from fuggers_py._core.errors import FuggersError
from fuggers_py._core.ids import YearMonth as YearMonthId
from fuggers_py._core.types import Date


@dataclass(frozen=True, slots=True)
class InflationError(FuggersError):
    """Base exception for inflation-convention and reference-index failures."""


@dataclass(frozen=True, slots=True)
class InvalidObservationLag(InflationError):
    """Raised when an inflation convention carries an invalid observation lag."""

    observation_lag_months: int

    def __str__(self) -> str:  # pragma: no cover - trivial
        return (
            "Invalid inflation observation lag: "
            f"{self.observation_lag_months}. observation_lag_months must be non-negative."
        )


@dataclass(frozen=True, slots=True)
class UnsupportedInflationInterpolation(InflationError):
    """Raised when reference-index resolution does not support the convention."""

    interpolation_method: object

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Unsupported inflation interpolation method: {self.interpolation_method!r}."


@dataclass(frozen=True, slots=True)
class MissingInflationFixing(InflationError):
    """Raised when required monthly inflation fixings are not available."""

    index_name: str
    requested_date: Date
    observation_months: tuple[YearMonthId, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "index_name", self.index_name.strip().upper())
        object.__setattr__(
            self,
            "observation_months",
            tuple(YearMonth.parse(observation_month) for observation_month in self.observation_months),
        )

    def __str__(self) -> str:  # pragma: no cover - trivial
        months = ", ".join(observation_month.as_str() for observation_month in self.observation_months)
        return (
            f"Missing inflation fixing for {self.index_name} required to resolve reference CPI on "
            f"{self.requested_date}: {months}."
        )


__all__ = [
    "InflationError",
    "InvalidObservationLag",
    "MissingInflationFixing",
    "UnsupportedInflationInterpolation",
]
