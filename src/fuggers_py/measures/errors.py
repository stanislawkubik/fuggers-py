"""Analytics-layer exception hierarchy.

The analytics namespace mirrors the bond-layer error model but uses its own
root type so callers can catch analytics failures explicitly while still
working with the shared package conventions.
"""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py.core.errors import FuggersError


class AnalyticsError(FuggersError):
    """Base exception for all analytics-layer errors.

    The class also provides factory constructors that return the more specific
    analytics exception types used throughout the package.
    """

    @classmethod
    def invalid_input(cls, reason: str) -> InvalidInput:
        """Return an :class:`InvalidInput` for malformed analytics input."""

        return InvalidInput(reason=reason)

    @classmethod
    def invalid_settlement(cls, reason: str) -> InvalidSettlement:
        """Return an :class:`InvalidSettlement` for invalid settlement data."""

        return InvalidSettlement(reason=reason)

    @classmethod
    def yield_solver_failed(cls, reason: str) -> YieldSolverError:
        """Return a :class:`YieldSolverError` for solver failures."""

        return YieldSolverError(reason=reason)

    @classmethod
    def pricing_failed(cls, reason: str) -> PricingError:
        """Return a :class:`PricingError` for pricing failures."""

        return PricingError(reason=reason)

    @classmethod
    def spread_failed(cls, reason: str) -> SpreadError:
        """Return a :class:`SpreadError` for spread-calculation failures."""

        return SpreadError(reason=reason)


@dataclass(frozen=True, slots=True)
class InvalidInput(AnalyticsError):
    """Raised when an analytics helper receives malformed input."""

    reason: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Invalid input: {self.reason}"


@dataclass(frozen=True, slots=True)
class InvalidSettlement(AnalyticsError):
    """Raised when settlement inputs are inconsistent or unsupported."""

    reason: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Invalid settlement: {self.reason}"


@dataclass(frozen=True, slots=True)
class YieldSolverError(AnalyticsError):
    """Raised when yield solving fails to converge or validate."""

    reason: str

    def __str__(self) -> str:
        return f"Yield solver failed: {self.reason}"


@dataclass(frozen=True, slots=True)
class PricingError(AnalyticsError):
    """Raised when analytics pricing cannot complete successfully."""

    reason: str

    def __str__(self) -> str:
        return f"Pricing failed: {self.reason}"


@dataclass(frozen=True, slots=True)
class SpreadError(AnalyticsError):
    """Raised when spread calculations fail."""

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
