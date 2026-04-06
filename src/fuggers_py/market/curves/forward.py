"""Forward curve wrapper for discount-factor implied forward rates.

The curve reports a continuously compounded forward rate for each tenor by
comparing discount factors over a fixed forward horizon.
"""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py.core.types import Compounding, Date

from .errors import InvalidCurveInput
from .term_structure import TermStructure
from .value_type import ValueType
from .wrappers import RateCurve


@dataclass(frozen=True, slots=True)
class ForwardCurve(TermStructure):
    """Forward-rate term structure implied by a discount curve.

    Parameters
    ----------
    discount_curve:
        Discount-factor curve used to infer the forward rate.
    _forward_tenor:
        Forward horizon in years. The horizon must be strictly positive.
    """

    discount_curve: RateCurve
    _forward_tenor: float

    @classmethod
    def new(cls, discount_curve: RateCurve, forward_tenor: float) -> "ForwardCurve":
        """Construct a forward curve for a fixed tenor horizon."""
        tenor = float(forward_tenor)
        if tenor <= 0.0:
            raise InvalidCurveInput("Forward tenor must be positive.")
        return cls(discount_curve=discount_curve, _forward_tenor=tenor)

    @classmethod
    def from_months(cls, discount_curve: RateCurve, months: int) -> "ForwardCurve":
        """Construct a forward curve from a tenor expressed in months."""
        m = int(months)
        if m <= 0:
            raise InvalidCurveInput("months must be positive.")
        return cls.new(discount_curve, float(m) / 12.0)

    def forward_tenor(self) -> float:
        """Return the forward horizon in years."""
        return float(self._forward_tenor)

    def reference_date(self) -> Date:
        """Return the reference date of the underlying discount curve."""
        return self.discount_curve.reference_date()

    def tenor_bounds(self) -> tuple[float, float]:
        """Return the tenor range over which the forward horizon fits."""
        lo, hi = self.discount_curve.curve.tenor_bounds()
        max_t = float(hi) - float(self._forward_tenor)
        return float(lo), float(max_t)

    def value_type(self) -> ValueType:
        """Return a continuously compounded forward-rate value type."""
        return ValueType.forward_rate(self._forward_tenor, compounding=Compounding.CONTINUOUS)

    def forward_rate_at(self, t: float) -> float:
        """Return the continuously compounded forward rate at tenor ``t``."""
        tau = float(t)
        return self.discount_curve.forward_rate_at_tenors(
            tau,
            tau + float(self._forward_tenor),
            compounding=Compounding.CONTINUOUS,
        )

    def value_at(self, t: float) -> float:
        """Alias for :meth:`forward_rate_at`."""
        return self.forward_rate_at(t)

    def max_date(self) -> Date:
        """Return the maximum date supported by the underlying discount curve."""
        return self.discount_curve.max_date()
