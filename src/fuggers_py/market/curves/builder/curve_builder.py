"""Compatibility-focused curve builders.

This builder mirrors the higher-level curve construction API used by the
analytics layer. Inputs are raw decimals and tenors are expressed in years
from the reference date, so the resulting term structure is ready for
market-layer consumers without additional conversion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Protocol

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Compounding, Date

from ..calibration.instruments import CalibrationInstrument
from ..discrete import DiscreteCurve, ExtrapolationMethod, InterpolationMethod
from ..errors import BuilderError, MixedPillarTypes
from ..segmented import SegmentBuilder, SegmentedCurve
from ..term_structure import TermStructure
from ..value_type import ValueType
from ..wrappers import CreditCurve


class CurveFamily(str, Enum):
    """Curve families supported by :class:`CurveBuilder`.

    The family determines the semantic value type used by the constructed
    curve and which object is returned.
    """

    DISCOUNT = "DISCOUNT"
    ZERO = "ZERO"
    FORWARD = "FORWARD"
    CREDIT = "CREDIT"
    SURVIVAL_PROBABILITY = "SURVIVAL_PROBABILITY"
    HAZARD_RATE = "HAZARD_RATE"
    CREDIT_SPREAD = "CREDIT_SPREAD"


class InstrumentType(str, Enum):
    """Instrument families accepted by curve-calibration pipelines."""

    DEPOSIT = "DEPOSIT"
    FRA = "FRA"
    FUTURE = "FUTURE"
    OIS = "OIS"
    SWAP = "SWAP"
    BASIS_SWAP = "BASIS_SWAP"
    CUSTOM = "CUSTOM"


class CurveInstrument(Protocol):
    """Protocol for instruments that can be used by curve builders."""

    instrument_type: InstrumentType

    def maturity_date(self) -> Date:
        ...


def _float(x: object) -> float:
    if isinstance(x, Decimal):
        return float(x)
    return float(x)


@dataclass(slots=True)
class CurveBuilder:
    """Build rate or credit curves from pillars or segment builders.

    The builder chooses the stored
    :class:`~fuggers_py.market.curves.value_type.ValueType` from the configured
    family. Credit families return
    :class:`~fuggers_py.market.curves.wrappers.CreditCurve` wrappers; all other
    families return raw
    :class:`~fuggers_py.market.curves.term_structure.TermStructure` objects.

    Attributes
    ----------
    reference_date
        Curve anchor date used to interpret tenor inputs.
    family
        Curve family that determines the semantic value type.
    interpolation_method
        Interpolation scheme applied to discrete pillars, if any.
    extrapolation_method
        Extrapolation scheme applied outside the pillar range.
    zero_compounding
        Compounding convention used when zero-rate pillars are present.
    zero_day_count
        Day-count convention used for zero-rate pillars.
    recovery_rate
        Fractional recovery used by credit-family wrappers.
    """

    reference_date: Date
    family: CurveFamily = CurveFamily.DISCOUNT
    interpolation_method: InterpolationMethod | None = None
    extrapolation_method: ExtrapolationMethod = ExtrapolationMethod.FLAT
    zero_compounding: Compounding = Compounding.CONTINUOUS
    zero_day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED
    recovery_rate: Decimal = Decimal("0.4")
    _tenors: list[float] = field(default_factory=list)
    _values: list[float] = field(default_factory=list)
    _pillar_kind: str | None = None
    _segments: list[SegmentBuilder] = field(default_factory=list)

    @classmethod
    def discount(cls, reference_date: Date) -> "CurveBuilder":
        """Return a builder configured for discount-factor curves."""

        return cls(reference_date=reference_date, family=CurveFamily.DISCOUNT)

    @classmethod
    def zero(cls, reference_date: Date) -> "CurveBuilder":
        """Return a builder configured for zero-rate curves."""

        return cls(reference_date=reference_date, family=CurveFamily.ZERO)

    @classmethod
    def credit(
        cls,
        reference_date: Date,
        *,
        family: CurveFamily = CurveFamily.SURVIVAL_PROBABILITY,
        recovery_rate: Decimal = Decimal("0.4"),
    ) -> "CurveBuilder":
        """Return a builder configured for credit-curve families."""

        return cls(reference_date=reference_date, family=family, recovery_rate=recovery_rate)

    def with_family(self, family: CurveFamily) -> "CurveBuilder":
        """Set the curve family that determines the output value type."""

        self.family = family
        return self

    def with_interpolation(self, method: InterpolationMethod) -> "CurveBuilder":
        """Set the interpolation method used for discrete curves."""

        self.interpolation_method = method
        return self

    def with_extrapolation(self, method: ExtrapolationMethod) -> "CurveBuilder":
        """Set the extrapolation method used for discrete curves."""

        self.extrapolation_method = method
        return self

    def with_recovery_rate(self, recovery_rate: object) -> "CurveBuilder":
        """Set the recovery rate used by credit-curve wrappers."""

        self.recovery_rate = Decimal(str(recovery_rate))
        return self

    def add_pillar(self, tenor: float, value: object) -> "CurveBuilder":
        """Add a raw-value pillar at a tenor in years."""

        if self._pillar_kind not in (None, "value"):
            raise MixedPillarTypes("Cannot mix explicit value pillars with zero-rate pillars.")
        self._pillar_kind = "value"
        self._tenors.append(float(tenor))
        self._values.append(_float(value))
        return self

    def add_zero_rate(self, tenor: float, rate: object) -> "CurveBuilder":
        """Add a zero-rate pillar at a tenor in years."""

        if self._pillar_kind not in (None, "zero"):
            raise MixedPillarTypes("Cannot mix explicit value pillars with zero-rate pillars.")
        self._pillar_kind = "zero"
        self._tenors.append(float(tenor))
        self._values.append(_float(rate))
        return self

    def add_segment(self, segment: SegmentBuilder) -> "CurveBuilder":
        """Add a segment builder to be assembled into a segmented curve."""

        self._segments.append(segment)
        return self

    def build(self):
        """Return the configured curve object."""

        value_type = self._resolve_value_type()
        interpolation = self.interpolation_method or self._default_interpolation(value_type=value_type)

        if self._segments:
            curve = SegmentedCurve(self.reference_date, self._segments, value_type=value_type)
            return self._wrap_curve(curve)

        if not self._tenors:
            raise BuilderError("No pillars or segments added.")

        curve = DiscreteCurve(
            self.reference_date,
            self._tenors,
            self._values,
            value_type=value_type,
            interpolation_method=interpolation,
            extrapolation_method=self.extrapolation_method,
        )
        return self._wrap_curve(curve)

    def _resolve_value_type(self) -> ValueType:
        """Resolve the value type implied by the curve family and pillars."""

        if self.family is CurveFamily.DISCOUNT:
            return ValueType.discount_factor()
        if self.family in {CurveFamily.ZERO, CurveFamily.FORWARD} or self._pillar_kind == "zero":
            return ValueType.zero_rate(self.zero_compounding, self.zero_day_count)
        if self.family is CurveFamily.SURVIVAL_PROBABILITY:
            return ValueType.survival_probability()
        if self.family is CurveFamily.HAZARD_RATE:
            return ValueType.hazard_rate()
        if self.family in {CurveFamily.CREDIT, CurveFamily.CREDIT_SPREAD}:
            return ValueType.credit_spread()
        return ValueType.discount_factor()

    @staticmethod
    def _default_interpolation(*, value_type: ValueType) -> InterpolationMethod:
        """Return the default interpolation for the resolved value type."""

        if value_type.kind.value in {"DISCOUNT_FACTOR", "SURVIVAL_PROBABILITY"}:
            return InterpolationMethod.LOG_LINEAR
        return InterpolationMethod.LINEAR

    def _wrap_curve(self, curve: TermStructure):
        """Wrap credit curves and leave rate curves as raw term structures."""

        if self.family in {
            CurveFamily.CREDIT,
            CurveFamily.SURVIVAL_PROBABILITY,
            CurveFamily.HAZARD_RATE,
            CurveFamily.CREDIT_SPREAD,
        }:
            return CreditCurve(curve, recovery_rate=self.recovery_rate)
        return curve


__all__ = [
    "CalibrationInstrument",
    "CurveBuilder",
    "CurveFamily",
    "CurveInstrument",
    "InstrumentType",
    "SegmentBuilder",
]
