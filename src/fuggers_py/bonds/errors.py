"""Bond-domain exception hierarchy."""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py._core.errors import FuggersError


class BondError(FuggersError):
    """Base exception for bond and bond-convention failures."""

    @classmethod
    def invalid_spec(cls, reason: str) -> "InvalidBondSpec":
        return InvalidBondSpec(reason=reason)

    @classmethod
    def missing_field(cls, field: str) -> "MissingRequiredField":
        return MissingRequiredField(field=field)

    @classmethod
    def pricing_failed(cls, reason: str) -> "BondPricingError":
        return BondPricingError(reason=reason)


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

    def __str__(self) -> str:
        return f"Invalid bond spec: {self.reason}"


@dataclass(frozen=True, slots=True)
class MissingRequiredField(BondError):
    """Raised when a required field is missing."""

    field: str

    def __str__(self) -> str:
        return f"Missing required field: {self.field}"


@dataclass(frozen=True, slots=True)
class BondPricingError(BondError):
    """Raised when pricing inputs do not admit a valid result."""

    reason: str

    def __str__(self) -> str:
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

    def __str__(self) -> str:
        return f"Schedule error: {self.reason}"


@dataclass(frozen=True, slots=True)
class SettlementError(BondError):
    """Raised when settlement-date resolution fails."""

    reason: str

    def __str__(self) -> str:
        return f"Settlement error: {self.reason}"


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
    "BondError",
    "IdentifierError",
    "InvalidInput",
    "InvalidIdentifier",
    "InvalidSettlement",
    "InvalidBondSpec",
    "MissingRequiredField",
    "BondPricingError",
    "YieldSolverError",
    "PricingError",
    "SpreadError",
    "YieldConvergenceFailed",
    "ScheduleError",
    "SettlementError",
]
