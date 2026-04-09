"""Multi-curve environment helpers.

The environment separates discount curves by currency from projection curves
by :class:`~fuggers_py.market.curves.multicurve.index.RateIndex`. Missing
entries raise :class:`MissingCurveError` instead of silently falling back, so
callers have to make the curve choice explicit.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fuggers_py.core.types import Currency

from ..errors import MissingCurveError
from ..term_structure import TermStructure
from .index import RateIndex


@dataclass(frozen=True, slots=True)
class MultiCurveEnvironment:
    """Bundle discount and projection curves for multi-curve pricing.

    Attributes
    ----------
    discount_curves
        Mapping from currency to discount curve.
    projection_curves
        Mapping from :class:`RateIndex` to projection curve.
    """

    discount_curves: dict[Currency, TermStructure]
    projection_curves: dict[RateIndex, TermStructure]

    def discount_curve(self, currency: Currency) -> TermStructure:
        """Return the discount curve for ``currency``.

        Parameters
        ----------
        currency
            Currency whose discount curve should be returned.
        """

        try:
            return self.discount_curves[currency]
        except KeyError as exc:  # pragma: no cover - simple
            raise MissingCurveError(f"Missing discount curve for currency {currency}.") from exc

    def projection_curve(self, index: RateIndex) -> TermStructure:
        """Return the projection curve for ``index``.

        Parameters
        ----------
        index
            Rate index whose projection curve should be returned.
        """

        try:
            return self.projection_curves[index]
        except KeyError as exc:  # pragma: no cover - simple
            raise MissingCurveError(f"Missing projection curve for index {index}.") from exc


@dataclass(slots=True)
class MultiCurveEnvironmentBuilder:
    """Incrementally assemble a :class:`MultiCurveEnvironment`."""

    _discount_curves: dict[Currency, TermStructure] = field(default_factory=dict)
    _projection_curves: dict[RateIndex, TermStructure] = field(default_factory=dict)

    def add_discount_curve(self, currency: Currency, curve: TermStructure) -> "MultiCurveEnvironmentBuilder":
        """Register a discount curve for ``currency``."""

        self._discount_curves[currency] = curve
        return self

    def add_projection_curve(self, index: RateIndex, curve: TermStructure) -> "MultiCurveEnvironmentBuilder":
        """Register a projection curve for ``index``."""

        self._projection_curves[index] = curve
        return self

    def build(self) -> MultiCurveEnvironment:
        """Return an immutable snapshot of the configured curves."""

        return MultiCurveEnvironment(
            discount_curves=dict(self._discount_curves),
            projection_curves=dict(self._projection_curves),
        )


__all__ = [
    "MissingCurveError",
    "MultiCurveEnvironment",
    "MultiCurveEnvironmentBuilder",
]
