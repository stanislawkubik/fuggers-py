"""Rate-curve wrapper helpers.

These adapters translate a generic term structure into the core
``YieldCurve`` protocol. The wrapped curve is still responsible for the curve
date and tenor interpretation; the wrapper only converts between raw node
conventions and the yield-curve methods.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.core.traits import YieldCurve
from fuggers_py.core.types import Compounding, Date, Yield

from ..conversion import ValueConverter
from ..errors import InvalidCurveInput, UnsupportedValueType
from .._semantics import stored_value_type
from ..term_structure import TermStructure
from ..value_type import ValueTypeKind


def _decimal_from_float(x: float) -> Decimal:
    return Decimal(str(float(x)))


@dataclass(frozen=True, slots=True)
class RateCurve(YieldCurve):
    """Adapt a generic term structure to the yield-curve protocol.

    The wrapped curve may store discount factors or zero rates.  Survival
    probabilities are treated as discount-factor-like quantities for the
    purpose of forward and zero-rate conversion.

    Attributes
    ----------
    curve
        Wrapped term structure used for all tenor lookups.
    """

    curve: TermStructure

    def date(self) -> Date:
        """Return the wrapped curve date."""

        return self.curve.date()

    def _date_to_tenor(self, date: Date) -> float:
        """Convert a calendar date to a tenor using the wrapped curve."""

        return self.curve.date_to_tenor(date)

    def discount_factor_at_tenor(self, t: float) -> float:
        """Return a discount factor at tenor ``t`` in years.

        The tenor is interpreted in year fractions from the reference date.
        """

        tau = float(t)
        if tau <= 0.0:
            return 1.0

        vt = stored_value_type(self.curve)
        match vt.kind:
            case ValueTypeKind.DISCOUNT_FACTOR:
                return float(self.curve.value_at_tenor(tau))
            case ValueTypeKind.ZERO_RATE:
                z = float(self.curve.value_at_tenor(tau))
                comp = vt.compounding or Compounding.CONTINUOUS
                return ValueConverter.zero_to_df(z, tau, comp)
            case ValueTypeKind.SURVIVAL_PROBABILITY:
                return float(self.curve.value_at_tenor(tau))
            case _:
                raise UnsupportedValueType(f"Cannot produce a discount factor from {vt}.")

    def zero_rate_at_tenor(self, t: float, *, compounding: Compounding = Compounding.CONTINUOUS) -> float:
        """Return a zero rate at tenor ``t`` under the requested compounding.

        When the wrapped curve already stores zero rates, the method converts
        between compounding conventions instead of recomputing from discount
        factors.
        """

        tau = float(t)
        if tau <= 0.0:
            return 0.0

        vt = stored_value_type(self.curve)
        match vt.kind:
            case ValueTypeKind.DISCOUNT_FACTOR:
                df = float(self.curve.value_at_tenor(tau))
                return ValueConverter.df_to_zero(df, tau, compounding)
            case ValueTypeKind.ZERO_RATE:
                z = float(self.curve.value_at_tenor(tau))
                stored = vt.compounding or Compounding.CONTINUOUS
                return ValueConverter.convert_compounding(z, stored, compounding)
            case _:
                raise UnsupportedValueType(f"Cannot produce a zero rate from {vt}.")

    def forward_rate_at_tenors(
        self,
        t1: float,
        t2: float,
        *,
        compounding: Compounding = Compounding.CONTINUOUS,
    ) -> float:
        """Return the forward rate between ``t1`` and ``t2`` in years.

        The forward is derived from the two discount factors implied by the
        wrapped curve and respects the requested compounding convention.
        """

        tau1 = float(t1)
        tau2 = float(t2)
        if tau2 <= tau1:
            raise InvalidCurveInput("End tenor must be after start tenor.")
        df1 = self.discount_factor_at_tenor(tau1)
        df2 = self.discount_factor_at_tenor(tau2)
        return ValueConverter.forward_rate_from_dfs(df1, df2, tau1, tau2, compounding)

    def discount_factor(self, date: Date) -> Decimal:
        """Return the discount factor to ``date`` as a raw decimal ``Decimal``."""

        t = self._date_to_tenor(date)
        return _decimal_from_float(self.discount_factor_at_tenor(t))

    def zero_rate(self, date: Date) -> Yield:
        """Return the continuous zero rate to ``date`` as a core ``Yield``."""

        t = self._date_to_tenor(date)
        r = self.zero_rate_at_tenor(t, compounding=Compounding.CONTINUOUS)
        return Yield.new(_decimal_from_float(r), Compounding.CONTINUOUS)


__all__ = ["RateCurve"]
