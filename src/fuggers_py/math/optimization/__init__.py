"""Optimization routines for fitting parameters and least-squares systems.

The public API includes gradient descent, Gauss-Newton, and a small
Levenberg-Marquardt variant together with their configuration/result types.
"""

from __future__ import annotations

from .gradient_descent import gradient_descent
from .least_squares import gauss_newton, levenberg_marquardt
from .types import OptimizationConfig, OptimizationResult

__all__ = [
    "OptimizationConfig",
    "OptimizationResult",
    "gradient_descent",
    "gauss_newton",
    "levenberg_marquardt",
]
