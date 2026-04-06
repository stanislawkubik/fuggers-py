"""Extrapolation interfaces and method enum.

The extrapolation layer is intentionally small. It lets the interpolation code
state whether values outside the observed range are extended flat, linearly, or
with a Smith-Wilson discount-factor fit.
"""

from __future__ import annotations

from enum import Enum
from typing import Protocol


class Extrapolator(Protocol):
    """Protocol for one-dimensional extrapolators.

    Implementations should accept a scalar query point and return the
    extrapolated value together with the implied first derivative.
    """

    def extrapolate(self, x: float) -> float:  # pragma: no cover - protocol
        ...

    def derivative(self, x: float) -> float:  # pragma: no cover - protocol
        ...


class ExtrapolationMethod(str, Enum):
    """Supported extrapolation schemes for curve construction."""

    FLAT = "FLAT"
    LINEAR = "LINEAR"
    SMITH_WILSON = "SMITH_WILSON"
