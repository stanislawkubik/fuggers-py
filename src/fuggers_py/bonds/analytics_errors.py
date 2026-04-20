"""Analytics-layer exceptions owned by the public bonds package."""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py._core.errors import FuggersError


class AnalyticsError(FuggersError):
    """Base exception for bond analytics failures."""

    @classmethod
    def invalid_input(cls, reason: str) -> "InvalidInput":
        return InvalidInput(reason=reason)

    @classmethod
    def invalid_settlement(cls, reason: str) -> "InvalidSettlement":
        return InvalidSettlement(reason=reason)

    @classmethod
    def yield_solver_failed(cls, reason: str) -> "YieldSolverError":
        return YieldSolverError(reason=reason)

    @classmethod
    def pricing_failed(cls, reason: str) -> "PricingError":
        return PricingError(reason=reason)

    @classmethod
    def spread_failed(cls, reason: str) -> "SpreadError":
        return SpreadError(reason=reason)


@dataclass(frozen=True, slots=True)
class InvalidInput(AnalyticsError):
    reason: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Invalid input: {self.reason}"


@dataclass(frozen=True, slots=True)
class InvalidSettlement(AnalyticsError):
    reason: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Invalid settlement: {self.reason}"


@dataclass(frozen=True, slots=True)
class YieldSolverError(AnalyticsError):
    reason: str

    def __str__(self) -> str:
        return f"Yield solver failed: {self.reason}"


@dataclass(frozen=True, slots=True)
class PricingError(AnalyticsError):
    reason: str

    def __str__(self) -> str:
        return f"Pricing failed: {self.reason}"


@dataclass(frozen=True, slots=True)
class SpreadError(AnalyticsError):
    reason: str

    def __str__(self) -> str:
        return f"Spread calculation failed: {self.reason}"


__all__ = [
    "AnalyticsError",
    "InvalidInput",
    "InvalidSettlement",
    "YieldSolverError",
    "PricingError",
    "SpreadError",
]
