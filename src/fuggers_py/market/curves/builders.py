"""Simple builders for common rate curves.

The builders in this module construct
:class:`~fuggers_py.market.curves.wrappers.RateCurve` instances from tenor-based
or date-based inputs. Node values are raw decimals and tenors are interpreted
as year fractions from the reference date.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Compounding, Date

from .builder import CurveBuilder, CurveFamily, SegmentBuilder
from .discrete import DiscreteCurve, ExtrapolationMethod, InterpolationMethod
from .errors import BuilderError, MixedPillarTypes
from .value_type import ValueType
from .wrappers import RateCurve


def _float(x: object) -> float:
    if isinstance(x, Decimal):
        return float(x)
    return float(x)


@dataclass(slots=True)
class DiscountCurveBuilder:
    """Build a discount curve from tenor/value pillars.

    The builder accepts either discount factors or zero rates, but not both in
    the same instance.  Discount-factor pillars default to log-linear
    interpolation; zero-rate pillars default to linear interpolation.

    Attributes
    ----------
    reference_date
        Curve anchor date used to interpret tenor inputs.
    interpolation_method
        Interpolation scheme applied between pillars.
    extrapolation_method
        Extrapolation scheme applied outside the pillar range.
    zero_compounding
        Compounding convention used when zero-rate pillars are supplied.
    zero_day_count
        Day-count convention attached to zero-rate pillars.
    """

    reference_date: Date
    interpolation_method: InterpolationMethod | None = None
    extrapolation_method: ExtrapolationMethod = ExtrapolationMethod.FLAT
    zero_compounding: Compounding = Compounding.CONTINUOUS
    zero_day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED
    _tenors: list[float] = field(default_factory=list)
    _values: list[float] = field(default_factory=list)
    _pillar_kind: str | None = None  # "df" or "zero"

    def add_pillar(self, tenor: float, discount_factor: object) -> "DiscountCurveBuilder":
        """Add a discount-factor pillar at a tenor in years."""

        if self._pillar_kind not in (None, "df"):
            raise MixedPillarTypes("Cannot mix discount-factor and zero-rate pillars.")
        self._pillar_kind = "df"
        self._tenors.append(float(tenor))
        self._values.append(_float(discount_factor))
        return self

    def add_zero_rate(self, tenor: float, rate: object) -> "DiscountCurveBuilder":
        """Add a zero-rate pillar at a tenor in years."""

        if self._pillar_kind not in (None, "zero"):
            raise MixedPillarTypes("Cannot mix discount-factor and zero-rate pillars.")
        self._pillar_kind = "zero"
        self._tenors.append(float(tenor))
        self._values.append(_float(rate))
        return self

    def with_interpolation(self, method: InterpolationMethod) -> "DiscountCurveBuilder":
        """Set the interpolation method used when building the curve."""

        self.interpolation_method = method
        return self

    def with_extrapolation(
        self, method: ExtrapolationMethod = ExtrapolationMethod.FLAT
    ) -> "DiscountCurveBuilder":
        """Set the extrapolation method used when building the curve."""

        self.extrapolation_method = method
        return self

    def build(self) -> RateCurve:
        """Return the configured discount curve as a yield-curve wrapper."""

        if not self._tenors:
            raise BuilderError("No pillars added.")
        if self._pillar_kind is None:
            raise BuilderError("Pillar type is unknown; add pillars before building.")

        if self._pillar_kind == "df":
            value_type = ValueType.discount_factor()
            interp_default = InterpolationMethod.LOG_LINEAR
        else:
            value_type = ValueType.zero_rate(self.zero_compounding, self.zero_day_count)
            interp_default = InterpolationMethod.LINEAR

        interpolation = self.interpolation_method or interp_default

        curve = DiscreteCurve(
            self.reference_date,
            self._tenors,
            self._values,
            value_type=value_type,
            interpolation_method=interpolation,
            extrapolation_method=self.extrapolation_method,
        )
        return RateCurve(curve)


@dataclass(slots=True)
class ZeroCurveBuilder:
    """Build a zero curve from calendar-date pillars.

    Input dates are converted to year fractions using the configured day-count
    convention, and the stored rates are interpreted using the configured
    compounding convention.

    Attributes
    ----------
    reference_date
        Curve anchor date used to convert calendar pillars to tenors.
    day_count
        Day-count convention used to compute year fractions.
    compounding
        Compounding convention associated with stored zero rates.
    """

    reference_date: Date
    day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED
    compounding: Compounding = Compounding.CONTINUOUS
    interpolation_method: InterpolationMethod = InterpolationMethod.LINEAR
    extrapolation_method: ExtrapolationMethod = ExtrapolationMethod.FLAT
    _dates: list[Date] = field(default_factory=list)
    _rates: list[float] = field(default_factory=list)

    def add_rate(self, date: Date, rate: object) -> "ZeroCurveBuilder":
        """Add a zero-rate pillar on or after the reference date."""

        if date < self.reference_date:
            raise BuilderError("ZeroCurveBuilder requires dates on/after the reference date.")
        self._dates.append(date)
        self._rates.append(_float(rate))
        return self

    def with_interpolation(self, method: InterpolationMethod) -> "ZeroCurveBuilder":
        """Set the interpolation method used when building the curve."""

        self.interpolation_method = method
        return self

    def with_extrapolation(self, method: ExtrapolationMethod = ExtrapolationMethod.FLAT) -> "ZeroCurveBuilder":
        """Set the extrapolation method used when building the curve."""

        self.extrapolation_method = method
        return self

    def build(self) -> RateCurve:
        """Return the configured zero curve as a yield-curve wrapper."""

        if not self._dates:
            raise BuilderError("No rates added.")

        dc = self.day_count.to_day_count()
        tenors = [float(dc.year_fraction(self.reference_date, d)) for d in self._dates]
        value_type = ValueType.zero_rate(self.compounding, self.day_count)

        curve = DiscreteCurve(
            self.reference_date,
            tenors,
            self._rates,
            value_type=value_type,
            interpolation_method=self.interpolation_method,
            extrapolation_method=self.extrapolation_method,
        )
        return RateCurve(curve)


__all__ = [
    "CurveBuilder",
    "CurveFamily",
    "DiscountCurveBuilder",
    "SegmentBuilder",
    "ZeroCurveBuilder",
]
