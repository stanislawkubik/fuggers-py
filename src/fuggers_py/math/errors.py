"""Exception hierarchy for :mod:`fuggers_py.math`.

The math layer raises structured exceptions for invalid inputs, singular
systems, convergence failures, and extrapolation violations. Payload fields are
kept small and explicit so callers can inspect the failing values directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py.core.errors import FuggersError


class MathError(FuggersError):
    """Base exception for all math-layer failures."""

    @classmethod
    def convergence_failed(cls, iterations: int, residual: float) -> ConvergenceFailed:
        """Construct a convergence failure with iteration count and residual."""

        return ConvergenceFailed(iterations=iterations, residual=residual)

    @classmethod
    def invalid_input(cls, reason: str) -> InvalidInput:
        """Construct an invalid-input error with the supplied reason."""

        return InvalidInput(reason=reason)

    @classmethod
    def insufficient_data(cls, required: int, actual: int) -> InsufficientData:
        """Construct an insufficient-data error with the required and actual counts."""

        return InsufficientData(required=required, actual=actual)


@dataclass(frozen=True, slots=True)
class ConvergenceFailed(MathError):
    """Raised when an iterative algorithm stops before meeting tolerance.

    Attributes
    ----------
    iterations:
        Number of iterations completed before the failure was detected.
    residual:
        Absolute residual or objective measure at the last iterate.
    """

    iterations: int
    residual: float

    def __str__(self) -> str:
        return (
            f"Convergence failed after {self.iterations} iterations "
            f"(residual={self.residual:.6g})."
        )


@dataclass(frozen=True, slots=True)
class InvalidBracket(MathError):
    """Raised when a bracketed root solver does not receive a valid bracket.

    The bracket is valid only when the endpoint function values have opposite
    signs or one endpoint is already a root.
    """

    a: float
    b: float
    fa: float
    fb: float

    def __str__(self) -> str:
        return (
            "Invalid bracket: f(a) and f(b) must have opposite signs "
            f"(a={self.a:.6g}, b={self.b:.6g}, fa={self.fa:.6g}, fb={self.fb:.6g})."
        )


@dataclass(frozen=True, slots=True)
class DivisionByZero(MathError):
    """Raised when an algorithm divides by a zero or numerically zero pivot."""

    value: float

    def __str__(self) -> str:
        return f"Division by zero (value={self.value:.6g})."


@dataclass(frozen=True, slots=True)
class SingularMatrix(MathError):
    """Raised when a linear system or factorization is numerically singular."""

    def __str__(self) -> str:  # pragma: no cover - trivial
        return "Singular matrix."


@dataclass(frozen=True, slots=True)
class DimensionMismatch(MathError):
    """Raised when two arrays or matrices have incompatible dimensions."""

    rows1: int
    cols1: int
    rows2: int
    cols2: int

    def __str__(self) -> str:
        return (
            "Dimension mismatch: "
            f"({self.rows1}x{self.cols1}) vs ({self.rows2}x{self.cols2})."
        )


@dataclass(frozen=True, slots=True)
class ExtrapolationNotAllowed(MathError):
    """Raised when a value is requested outside the supported interpolation range."""

    x: float
    min: float
    max: float

    def __str__(self) -> str:
        return (
            f"Extrapolation not allowed at x={self.x:.6g} "
            f"(range=[{self.min:.6g}, {self.max:.6g}])."
        )


@dataclass(frozen=True, slots=True)
class InsufficientData(MathError):
    """Raised when an algorithm needs more observations than were supplied."""

    required: int
    actual: int

    def __str__(self) -> str:
        return f"Insufficient data: required {self.required}, got {self.actual}."


@dataclass(frozen=True, slots=True)
class InvalidInput(MathError):
    """Raised when an argument is finite but semantically invalid."""

    reason: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Invalid input: {self.reason}"


@dataclass(frozen=True, slots=True)
class MathOverflow(MathError):
    """Raised when a numerical operation overflows floating-point range."""

    operation: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Math overflow during {self.operation}."


@dataclass(frozen=True, slots=True)
class MathUnderflow(MathError):
    """Raised when a numerical operation underflows floating-point range."""

    operation: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Math underflow during {self.operation}."
