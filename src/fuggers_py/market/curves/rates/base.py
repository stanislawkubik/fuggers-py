"""Base public abstraction for rates term structures."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod

from fuggers_py.core.types import Date

from ..errors import InvalidCurveInput, TenorOutOfBounds
from .enums import ExtrapolationPolicy, RateSpace
from .spec import CurveSpec


class RatesTermStructure(ABC):
    """Public root for rate term structures.

    Every public rates curve carries one immutable :class:`CurveSpec`, exposes
    one rate-space meaning, and declares a finite tenor domain.
    """

    __slots__ = ("_spec",)

    def __init__(self, spec: CurveSpec) -> None:
        if not isinstance(spec, CurveSpec):
            raise InvalidCurveInput("spec must be a CurveSpec.")
        self._spec = spec

    @property
    def spec(self) -> CurveSpec:
        """Return the immutable business identity of the curve."""

        return self._spec

    @property
    def reference_date(self) -> Date:
        """Return the curve anchor date."""

        return self._spec.reference_date

    @property
    @abstractmethod
    def rate_space(self) -> RateSpace:
        """Return the meaning of ``rate_at(tenor)``."""

    @abstractmethod
    def max_t(self) -> float:
        """Return the inclusive upper tenor bound in years."""

    @abstractmethod
    def rate_at(self, tenor: float) -> float:
        """Return the rate at tenor ``tenor`` in years, expressed in ``rate_space``."""

    def _validated_max_t(self) -> float:
        max_t = float(self.max_t())
        if not math.isfinite(max_t) or max_t < 0.0:
            raise InvalidCurveInput("max_t() must return a finite value >= 0.")
        return max_t

    def _check_t(self, t: float) -> None:
        tenor = float(t)
        if not math.isfinite(tenor):
            raise InvalidCurveInput("t must be finite.")
        if tenor < 0.0:
            raise InvalidCurveInput("t must be >= 0.")
        max_t = self._validated_max_t()
        if tenor > max_t and self.spec.extrapolation_policy is ExtrapolationPolicy.ERROR:
            raise TenorOutOfBounds(t=tenor, min=0.0, max=max_t)

    def validate_rate(self, tenor: float) -> float:
        """Validate and return ``rate_at(tenor)`` on the supported domain."""

        self._check_t(tenor)
        value = float(self.rate_at(tenor))
        if not math.isfinite(value):
            raise InvalidCurveInput("rate_at(tenor) must be finite on the valid domain.")
        return value


__all__ = ["RatesTermStructure"]
