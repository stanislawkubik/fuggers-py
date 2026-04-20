"""Linear algebra helpers used by the numerical routines in ``fuggers_py``.

The public API covers LU decomposition, dense linear solves, and tridiagonal
systems. Failures are reported with structured math exceptions when the system
is singular or the shapes do not line up.
"""

from __future__ import annotations

from .lu import lu_decomposition
from .solve import solve_linear_system
from .tridiagonal import solve_tridiagonal

__all__ = ["lu_decomposition", "solve_linear_system", "solve_tridiagonal"]
