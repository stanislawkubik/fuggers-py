"""Linear extrapolation from a reference point and slope."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LinearExtrapolator:
    """Extend a straight line defined by ``(x0, y0)`` and ``slope``.

    The value is extended with the same slope beyond the observed range, so the
    derivative is constant everywhere.
    """

    x0: float
    y0: float
    slope: float

    def extrapolate(self, x: float) -> float:
        """Evaluate the extrapolated line at ``x``."""

        return float(self.y0 + self.slope * (float(x) - self.x0))

    def derivative(self, x: float) -> float:  # pragma: no cover - trivial
        """Return the constant line slope."""

        return float(self.slope)
