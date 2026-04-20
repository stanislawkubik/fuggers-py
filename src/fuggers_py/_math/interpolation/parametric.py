"""Parametric yield curve families (Nelson-Siegel and Svensson).

These families parameterize zero-rate curves directly from factor loadings and
decay terms. They are useful when a curve should be smooth, low-dimensional,
and well behaved for positive tenors.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..errors import InvalidInput
from ..utils import assert_finite


def _a(x: float) -> float:
    """(1 - exp(-x)) / x with a stable x→0 limit."""

    if abs(x) < 1e-8:
        return 1.0 - x / 2.0 + x * x / 6.0 - x**3 / 24.0
    return (1.0 - np.exp(-x)) / x


def _da_dx(x: float) -> float:
    if abs(x) < 1e-8:
        return -0.5 + x / 3.0 - (x * x) / 8.0 + x**3 / 30.0
    ex = float(np.exp(-x))
    return (ex * (x + 1.0) - 1.0) / (x * x)


def _b(x: float) -> float:
    """(1 - exp(-x)) / x - exp(-x) with a stable x→0 limit."""

    if abs(x) < 1e-8:
        return x / 2.0 - (x * x) / 3.0 + x**3 / 8.0 - x**4 / 30.0
    ex = float(np.exp(-x))
    return (1.0 - ex) / x - ex


def _db_dx(x: float) -> float:
    if abs(x) < 1e-8:
        return 0.5 - 2.0 * x / 3.0 + 3.0 * x * x / 8.0 - 2.0 * x**3 / 15.0
    ex = float(np.exp(-x))
    return _da_dx(x) + ex


@dataclass(frozen=True, slots=True)
class NelsonSiegel:
    """Nelson-Siegel zero-rate parameterization.

    Attributes
    ----------
    beta0, beta1, beta2:
        Level, slope, and curvature factors.
    tau:
        Positive decay parameter controlling the curve shape.
    """

    beta0: float
    beta1: float
    beta2: float
    tau: float
    _allow_extrapolation: bool = True

    @classmethod
    def new(cls, beta0: float, beta1: float, beta2: float, tau: float) -> "NelsonSiegel":
        """Construct a Nelson-Siegel curve from factor loadings and decay."""

        return cls(beta0=beta0, beta1=beta1, beta2=beta2, tau=tau)

    @property
    def allows_extrapolation(self) -> bool:
        return True

    def min_x(self) -> float:
        return 0.0

    def max_x(self) -> float:
        return float(np.inf)

    def in_range(self, x: float) -> bool:
        return float(x) >= 0.0

    def _validate_t(self, t: float) -> float:
        t = assert_finite(t, name="t")
        if t < 0.0:
            raise InvalidInput("t must be non-negative.")
        tau = assert_finite(self.tau, name="tau")
        if tau <= 0.0:
            raise InvalidInput("tau must be positive.")
        return t

    def interpolate(self, t: float) -> float:
        """Evaluate the zero-rate curve at tenor ``t``."""

        t = self._validate_t(t)
        x = t / self.tau if t != 0.0 else 0.0
        a = _a(x)
        b = _b(x)
        return float(self.beta0 + self.beta1 * a + self.beta2 * b)

    def derivative(self, t: float) -> float:
        """Evaluate the first derivative of the Nelson-Siegel curve."""

        t = self._validate_t(t)
        if t == 0.0:
            x = 0.0
        else:
            x = t / self.tau
        da = _da_dx(x)
        db = _db_dx(x)
        return float((self.beta1 * da + self.beta2 * db) / self.tau)


@dataclass(frozen=True, slots=True)
class Svensson:
    """Svensson zero-rate parameterization with two curvature terms."""

    beta0: float
    beta1: float
    beta2: float
    beta3: float
    tau1: float
    tau2: float
    _allow_extrapolation: bool = True

    @classmethod
    def new(
        cls,
        beta0: float,
        beta1: float,
        beta2: float,
        beta3: float,
        tau1: float,
        tau2: float,
    ) -> "Svensson":
        """Construct a Svensson curve from factor loadings and decay values."""

        return cls(beta0=beta0, beta1=beta1, beta2=beta2, beta3=beta3, tau1=tau1, tau2=tau2)

    @property
    def allows_extrapolation(self) -> bool:
        return True

    def min_x(self) -> float:
        return 0.0

    def max_x(self) -> float:
        return float(np.inf)

    def in_range(self, x: float) -> bool:
        return float(x) >= 0.0

    def _validate_t(self, t: float) -> float:
        t = assert_finite(t, name="t")
        if t < 0.0:
            raise InvalidInput("t must be non-negative.")
        tau1 = assert_finite(self.tau1, name="tau1")
        tau2 = assert_finite(self.tau2, name="tau2")
        if tau1 <= 0.0 or tau2 <= 0.0:
            raise InvalidInput("tau1 and tau2 must be positive.")
        return t

    def interpolate(self, t: float) -> float:
        """Evaluate the zero-rate curve at tenor ``t``."""

        t = self._validate_t(t)
        x1 = t / self.tau1 if t != 0.0 else 0.0
        x2 = t / self.tau2 if t != 0.0 else 0.0
        a1 = _a(x1)
        b1 = _b(x1)
        b2 = _b(x2)
        return float(self.beta0 + self.beta1 * a1 + self.beta2 * b1 + self.beta3 * b2)

    def derivative(self, t: float) -> float:
        """Evaluate the first derivative of the Svensson curve."""

        t = self._validate_t(t)
        x1 = t / self.tau1 if t != 0.0 else 0.0
        x2 = t / self.tau2 if t != 0.0 else 0.0
        da1 = _da_dx(x1)
        db1 = _db_dx(x1)
        db2 = _db_dx(x2)
        return float((self.beta1 * da1 + self.beta2 * db1) / self.tau1 + (self.beta3 * db2) / self.tau2)
