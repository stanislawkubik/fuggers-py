"""Scalar root-finding algorithms and their configuration/result types.

The public API includes bracketed methods, open methods, and small wrapper
classes that carry a reusable :class:`~fuggers_py.math.solvers.types.SolverConfig`.
Residuals are absolute scalar function values unless a caller provides a
different convention.
"""

from __future__ import annotations

from .bisection import BisectionSolver, bisection
from .brent import BrentSolver, brent
from .hybrid import HybridSolver, hybrid, hybrid_numerical
from .newton import NewtonSolver, newton_raphson, newton_raphson_numerical
from .secant import SecantSolver, secant
from .types import DEFAULT_MAX_ITERATIONS, DEFAULT_TOLERANCE, MathResult, RootFinder, Solver, SolverConfig, SolverResult

__all__ = [
    "DEFAULT_TOLERANCE",
    "DEFAULT_MAX_ITERATIONS",
    "SolverConfig",
    "SolverResult",
    "MathResult",
    "RootFinder",
    "Solver",
    "bisection",
    "BisectionSolver",
    "brent",
    "BrentSolver",
    "secant",
    "SecantSolver",
    "newton_raphson",
    "newton_raphson_numerical",
    "NewtonSolver",
    "hybrid",
    "hybrid_numerical",
    "HybridSolver",
]
