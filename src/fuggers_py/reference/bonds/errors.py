"""Bond-layer exceptions (`fuggers_py.reference.bonds.errors`).

Bond-specific validation and runtime failures raise structured exceptions
carrying the relevant payload for downstream diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py.core.errors import FuggersError


class BondError(FuggersError):
    """Base exception for bond product and bond-pricer errors."""

    @classmethod
    def invalid_spec(cls, reason: str) -> "InvalidBondSpec":
        """Create an exception for an internally inconsistent bond definition.

        Parameters
        ----------
        reason
            Human-readable explanation of the validation failure.

        Returns
        -------
        InvalidBondSpec
            Structured bond-specification error carrying ``reason``.
        """

        return InvalidBondSpec(reason=reason)

    @classmethod
    def missing_field(cls, field: str) -> "MissingRequiredField":
        """Create an exception for a required bond field that was omitted.

        Parameters
        ----------
        field
            Name of the missing field or attribute.

        Returns
        -------
        MissingRequiredField
            Structured error identifying the missing field.
        """

        return MissingRequiredField(field=field)

    @classmethod
    def pricing_failed(cls, reason: str) -> "BondPricingError":
        """Create an exception for a bond-pricing failure.

        Parameters
        ----------
        reason
            Human-readable explanation of why pricing could not complete.

        Returns
        -------
        BondPricingError
            Structured pricing error carrying ``reason``.
        """

        return BondPricingError(reason=reason)


class IdentifierError(BondError):
    """Raised when an instrument identifier is invalid."""


@dataclass(frozen=True, slots=True)
class InvalidIdentifier(IdentifierError):
    """Raised when a bond identifier fails format or checksum validation."""

    identifier_type: str
    value: str
    reason: str

    def __str__(self) -> str:
        return f"Invalid {self.identifier_type}: {self.value!r} ({self.reason})."


@dataclass(frozen=True, slots=True)
class InvalidBondSpec(BondError):
    """Raised when a bond definition is internally inconsistent."""

    reason: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Invalid bond spec: {self.reason}"


@dataclass(frozen=True, slots=True)
class MissingRequiredField(BondError):
    """Raised when a builder or constructor is missing a required field."""

    field: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Missing required field: {self.field}"


@dataclass(frozen=True, slots=True)
class BondPricingError(BondError):
    """Raised when bond pricing inputs do not admit a valid result."""

    reason: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Bond pricing error: {self.reason}"


@dataclass(frozen=True, slots=True)
class YieldConvergenceFailed(BondError):
    """Raised when a bond-yield root finder fails to converge."""

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
