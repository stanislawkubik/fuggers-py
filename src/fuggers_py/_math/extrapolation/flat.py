"""Flat (constant) extrapolation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FlatExtrapolator:
    """Return a constant level outside the interpolation range.

    This is the simplest extrapolation scheme: the value is held constant and
    the derivative is zero.
    """

    level: float

    def extrapolate(self, x: float) -> float:  # pragma: no cover - trivial
        """Return the stored constant level."""

        return float(self.level)

    def derivative(self, x: float) -> float:  # pragma: no cover - trivial
        """Return the zero derivative implied by constant extrapolation."""

        return 0.0
