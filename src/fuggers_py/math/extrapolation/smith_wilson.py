"""Smith-Wilson extrapolation for discount factors.

The Smith-Wilson method fits discount factors so they reproduce the observed
market inputs exactly and converge toward an ultimate forward rate at long
maturities.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..errors import InvalidInput
from ..linear_algebra import solve_linear_system
from ..numerical import finite_difference_derivative
from ..utils import assert_all_positive, assert_finite, assert_same_length, assert_strictly_increasing


def _wilson_kernel(t: float, u: float, *, alpha: float, ufr: float) -> float:
    """Wilson kernel ``W(t, u)`` used by the Smith-Wilson method."""

    m = min(t, u)
    M = max(t, u)
    exp_ufr = np.exp(-ufr * (t + u))
    term = alpha * m - np.exp(-alpha * M) * np.sinh(alpha * m)
    return float(exp_ufr * term)


@dataclass(frozen=True, slots=True)
class SmithWilson:
    """Smith-Wilson discount-factor extrapolator.

    The constructor fits the Wilson weights that reproduce the supplied market
    discount factors and force the long end to converge toward the specified
    ultimate forward rate (UFR).
    """

    ufr: float
    alpha: float
    maturities: NDArray[np.float64]
    discount_factors: NDArray[np.float64]
    weights: NDArray[np.float64]

    def __init__(
        self,
        maturities: ArrayLike,
        discount_factors: ArrayLike,
        *,
        ufr: float,
        alpha: float,
    ) -> None:
        """Fit Smith-Wilson weights from observed maturities and discount factors.

        Parameters
        ----------
        maturities:
            Strictly increasing positive maturities of the observed discount
            factors.
        discount_factors:
            Strictly positive discount factors observed at the supplied
            maturities.
        ufr:
            Ultimate forward rate used as the long-run asymptote.
        alpha:
            Positive convergence parameter controlling how quickly the curve
            approaches the UFR.
        """

        t = assert_strictly_increasing(maturities, name="maturities")
        p = assert_all_positive(discount_factors, name="discount_factors")
        assert_same_length(t, p, a_name="maturities", b_name="discount_factors")

        ufr_f = assert_finite(ufr, name="ufr")
        alpha_f = assert_finite(alpha, name="alpha")
        if alpha_f <= 0.0:
            raise InvalidInput("alpha must be positive.")
        if np.any(t <= 0.0):
            raise InvalidInput("maturities must be strictly positive.")

        n = int(t.size)
        w_mat = np.empty((n, n), dtype=float)
        for i in range(n):
            for j in range(n):
                w_mat[i, j] = _wilson_kernel(float(t[i]), float(t[j]), alpha=alpha_f, ufr=ufr_f)

        u_vec = np.exp(-ufr_f * t)
        m_vec = p - u_vec
        weights = solve_linear_system(w_mat, m_vec)

        object.__setattr__(self, "ufr", ufr_f)
        object.__setattr__(self, "alpha", alpha_f)
        object.__setattr__(self, "maturities", t)
        object.__setattr__(self, "discount_factors", p)
        object.__setattr__(self, "weights", weights)

    def _u(self, t: float) -> float:
        return float(np.exp(-self.ufr * t))

    def discount_factor(self, t: float) -> float:
        """Return the extrapolated discount factor at time ``t``."""

        t = assert_finite(t, name="t")
        if t < 0.0:
            raise InvalidInput("t must be non-negative.")
        base = self._u(t)
        k = np.array(
            [_wilson_kernel(t, float(u), alpha=self.alpha, ufr=self.ufr) for u in self.maturities],
            dtype=float,
        )
        return float(base + float(np.dot(self.weights, k)))

    def extrapolate(self, x: float) -> float:
        """Alias for :meth:`discount_factor`."""

        return self.discount_factor(float(x))

    def derivative(self, x: float) -> float:
        """Return a finite-difference derivative of the discount-factor curve."""

        return float(finite_difference_derivative(self.discount_factor, float(x), h=1e-6, method="central"))
