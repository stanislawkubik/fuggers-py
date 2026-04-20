"""Internal float- and NumPy-oriented numerical utilities for ``fuggers_py``.

`fuggers_py._math` owns root finding, interpolation, extrapolation, linear
algebra, and lightweight optimization helpers used by the internal
implementation packages.
"""

from __future__ import annotations

from .errors import (  # noqa: F401
    ConvergenceFailed,
    DivisionByZero,
    DimensionMismatch,
    ExtrapolationNotAllowed,
    InsufficientData,
    InvalidBracket,
    InvalidInput,
    MathError,
    MathOverflow,
    MathUnderflow,
    SingularMatrix,
)
from .extrapolation import (  # noqa: F401
    ExtrapolationMethod,
    Extrapolator,
    FlatExtrapolator,
    LinearExtrapolator,
    SmithWilson,
)
from .interpolation import (  # noqa: F401
    CubicSpline,
    FlatForward,
    Interpolator,
    LinearInterpolator,
    LogLinearInterpolator,
    MonotoneConvex,
    NelsonSiegel,
    Svensson,
)
from .linear_algebra import (  # noqa: F401
    lu_decomposition,
    solve_linear_system,
    solve_tridiagonal,
)
from .optimization import (  # noqa: F401
    OptimizationConfig,
    OptimizationResult,
    gauss_newton,
    gradient_descent,
    levenberg_marquardt,
)
from .solvers import (  # noqa: F401
    BisectionSolver,
    BrentSolver,
    HybridSolver,
    MathResult,
    NewtonSolver,
    RootFinder,
    SecantSolver,
    Solver,
    SolverConfig,
    SolverResult,
    bisection,
    brent,
    hybrid,
    hybrid_numerical,
    newton_raphson,
    newton_raphson_numerical,
    secant,
)

__all__ = [
    # Errors
    "MathError",
    "ConvergenceFailed",
    "InvalidBracket",
    "DivisionByZero",
    "SingularMatrix",
    "DimensionMismatch",
    "ExtrapolationNotAllowed",
    "InsufficientData",
    "InvalidInput",
    "MathOverflow",
    "MathUnderflow",
    # Solvers
    "SolverConfig",
    "SolverResult",
    "MathResult",
    "RootFinder",
    "Solver",
    "BisectionSolver",
    "BrentSolver",
    "HybridSolver",
    "NewtonSolver",
    "SecantSolver",
    "bisection",
    "brent",
    "secant",
    "newton_raphson",
    "newton_raphson_numerical",
    "hybrid",
    "hybrid_numerical",
    # Interpolation
    "Interpolator",
    "LinearInterpolator",
    "LogLinearInterpolator",
    "CubicSpline",
    "FlatForward",
    "MonotoneConvex",
    "NelsonSiegel",
    "Svensson",
    # Extrapolation
    "Extrapolator",
    "ExtrapolationMethod",
    "FlatExtrapolator",
    "LinearExtrapolator",
    "SmithWilson",
    # Optimization
    "OptimizationConfig",
    "OptimizationResult",
    "gradient_descent",
    "gauss_newton",
    "levenberg_marquardt",
    # Linear algebra
    "lu_decomposition",
    "solve_linear_system",
    "solve_tridiagonal",
]
