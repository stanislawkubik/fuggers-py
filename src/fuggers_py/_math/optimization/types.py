"""Configuration and result types for the optimization helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class OptimizationConfig:
    """Configuration for gradient-based and least-squares optimization.

    Attributes
    ----------
    tolerance:
        Absolute stopping threshold used for gradient norms, objective changes,
        or similar residual measures.
    max_iterations:
        Maximum number of outer iterations.
    step_size:
        Finite-difference step used when approximating derivatives.
    armijo_c:
        Armijo sufficient-decrease constant for backtracking line search.
    backtracking_beta:
        Multiplicative factor applied to the step length during backtracking.
    min_step:
        Smallest step length accepted by backtracking before declaring failure.
    lm_initial_damping:
        Initial Levenberg-Marquardt damping factor.
    lm_damping_increase:
        Multiplicative increase applied when a LM trial step is rejected.
    lm_damping_decrease:
        Multiplicative decrease applied when a LM trial step is accepted.
    """

    tolerance: float = 1e-10
    max_iterations: int = 100
    step_size: float = 1e-8

    # Armijo / backtracking parameters
    armijo_c: float = 0.5
    backtracking_beta: float = 0.5
    min_step: float = 1e-15

    # Levenberg-Marquardt damping parameters (LM-lite)
    lm_initial_damping: float = 1e-3
    lm_damping_increase: float = 10.0
    lm_damping_decrease: float = 0.1


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    """Result returned by the optimization routines.

    Attributes
    ----------
    parameters:
        Best parameter vector found.
    objective_value:
        Objective value at ``parameters``.
    iterations:
        Number of outer iterations completed.
    converged:
        Whether the stopping criteria were satisfied before the iteration cap.
    """

    parameters: NDArray[np.float64]
    objective_value: float
    iterations: int
    converged: bool
