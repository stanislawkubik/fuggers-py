"""Root-finding interfaces and result/config types."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol, runtime_checkable

DEFAULT_TOLERANCE: float = 1e-10
DEFAULT_MAX_ITERATIONS: int = 100


@dataclass(frozen=True, slots=True)
class SolverConfig:
    """Configuration for scalar root-finding algorithms.

    Attributes
    ----------
    tolerance:
        Absolute stopping threshold applied to the scalar residual ``|f(x)|``.
    max_iterations:
        Maximum number of iterations allowed before raising convergence failure.
    """

    tolerance: float = DEFAULT_TOLERANCE
    max_iterations: int = DEFAULT_MAX_ITERATIONS

    def with_tolerance(self, tolerance: float) -> "SolverConfig":
        """Return a copy with ``tolerance`` replaced."""

        return replace(self, tolerance=float(tolerance))

    def with_max_iterations(self, max_iterations: int) -> "SolverConfig":
        """Return a copy with ``max_iterations`` replaced."""

        return replace(self, max_iterations=int(max_iterations))


@dataclass(frozen=True, slots=True)
class SolverResult:
    """Result returned by scalar root-finding algorithms.

    Attributes
    ----------
    root:
        Best root estimate.
    iterations:
        Number of iterations completed.
    residual:
        Absolute residual ``|f(root)|`` at the returned point.
    converged:
        Whether the solver met its stopping criteria.
    """

    root: float
    iterations: int
    residual: float
    converged: bool


@runtime_checkable
class RootFinder(Protocol):
    """Protocol for objects exposing a scalar root-finding entry point.

    Implementations should return a :class:`SolverResult` and follow the same
    absolute-residual convention as the free functions in this package.
    """

    def find_root(self, f, *args, **kwargs) -> SolverResult:  # pragma: no cover - protocol
        ...


# Public aliases for solver results and interfaces.
MathResult = SolverResult
Solver = RootFinder


__all__ = [
    "DEFAULT_TOLERANCE",
    "DEFAULT_MAX_ITERATIONS",
    "SolverConfig",
    "SolverResult",
    "MathResult",
    "RootFinder",
    "Solver",
]
