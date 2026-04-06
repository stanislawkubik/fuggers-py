"""Segmented curves with per-segment interpolation and sources.

Each segment owns its own source and interpolation settings, allowing the
overall curve to stitch together discrete curves, callables, or existing term
structures over disjoint tenor ranges.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

from fuggers_py.core.types import Date

from .errors import InvalidCurveInput
from .term_structure import TermStructure
from .value_type import ValueType
from .discrete import DiscreteCurve, ExtrapolationMethod, InterpolationMethod


SourceValue = TermStructure | Callable[[float], float] | Sequence[tuple[float, float]]


@dataclass(frozen=True, slots=True)
class SegmentSource:
    """Factory input describing a single curve segment."""

    source: SourceValue
    value_type: ValueType | None = None
    interpolation_method: InterpolationMethod | None = None
    extrapolation_method: ExtrapolationMethod | None = None

    @classmethod
    def from_curve(cls, curve: TermStructure) -> "SegmentSource":
        """Create a segment source from an existing term structure."""
        return cls(source=curve, value_type=curve.value_type())

    @classmethod
    def from_callable(
        cls,
        fn: Callable[[float], float],
        *,
        value_type: ValueType,
    ) -> "SegmentSource":
        """Create a segment source from a callable value function."""
        return cls(source=fn, value_type=value_type)

    @classmethod
    def from_pillars(
        cls,
        tenors: Sequence[float],
        values: Sequence[float],
        *,
        value_type: ValueType,
        interpolation_method: InterpolationMethod = InterpolationMethod.LINEAR,
        extrapolation_method: ExtrapolationMethod = ExtrapolationMethod.FLAT,
    ) -> "SegmentSource":
        """Create a segment source from tenor/value pillars."""
        pairs = tuple(zip(tenors, values, strict=True))
        return cls(
            source=pairs,
            value_type=value_type,
            interpolation_method=interpolation_method,
            extrapolation_method=extrapolation_method,
        )


@dataclass(frozen=True, slots=True)
class _CallableTermStructure(TermStructure):
    _reference_date: Date
    _fn: Callable[[float], float]
    _bounds: tuple[float, float]
    _value_type: ValueType

    def reference_date(self) -> Date:
        return self._reference_date

    def value_at(self, t: float) -> float:
        return float(self._fn(float(t)))

    def tenor_bounds(self) -> tuple[float, float]:
        return self._bounds

    def value_type(self) -> ValueType:
        return self._value_type

    def max_date(self) -> Date:
        return self.tenor_to_date(self._bounds[1])


@dataclass(frozen=True, slots=True)
class _Segment:
    start: float
    end: float
    curve: TermStructure

    def contains(self, tenor: float) -> bool:
        return self.start <= tenor <= self.end


@dataclass(slots=True)
class SegmentBuilder:
    """Mutable builder for a single segmented-curve interval."""

    start: float
    end: float
    source: SegmentSource | None = None
    interpolation_method: InterpolationMethod | None = None
    extrapolation_method: ExtrapolationMethod | None = None
    value_type: ValueType | None = None

    def with_source(self, source: SegmentSource) -> "SegmentBuilder":
        """Attach a segment source and inherit any explicit settings it carries."""
        self.source = source
        if source.value_type is not None:
            self.value_type = source.value_type
        if source.interpolation_method is not None:
            self.interpolation_method = source.interpolation_method
        if source.extrapolation_method is not None:
            self.extrapolation_method = source.extrapolation_method
        return self

    def with_curve(self, curve: TermStructure) -> "SegmentBuilder":
        """Attach an existing term structure as the segment source."""
        return self.with_source(SegmentSource.from_curve(curve))

    def with_callable(self, fn: Callable[[float], float], *, value_type: ValueType) -> "SegmentBuilder":
        """Attach a tenor-to-value callable as the segment source."""
        return self.with_source(SegmentSource.from_callable(fn, value_type=value_type))

    def with_pillars(
        self,
        tenors: Sequence[float],
        values: Sequence[float],
        *,
        value_type: ValueType,
        interpolation_method: InterpolationMethod = InterpolationMethod.LINEAR,
        extrapolation_method: ExtrapolationMethod = ExtrapolationMethod.FLAT,
    ) -> "SegmentBuilder":
        """Attach pillar data as the segment source."""
        return self.with_source(
            SegmentSource.from_pillars(
                tenors,
                values,
                value_type=value_type,
                interpolation_method=interpolation_method,
                extrapolation_method=extrapolation_method,
            )
        )

    def build(self, *, reference_date: Date, default_value_type: ValueType) -> _Segment:
        """Build the concrete segment for the requested reference date."""
        if self.end <= self.start:
            raise InvalidCurveInput("Segment end must be greater than segment start.")
        if self.source is None:
            raise InvalidCurveInput("SegmentBuilder requires a source.")

        source = self.source.source
        value_type = self.value_type or self.source.value_type or default_value_type
        if isinstance(source, TermStructure):
            curve = source
        elif callable(source):
            curve = _CallableTermStructure(reference_date, source, (float(self.start), float(self.end)), value_type)
        else:
            tenors = [float(t) for t, _ in source]
            values = [float(v) for _, v in source]
            curve = DiscreteCurve(
                reference_date,
                tenors,
                values,
                value_type=value_type,
                interpolation_method=self.interpolation_method or InterpolationMethod.LINEAR,
                extrapolation_method=self.extrapolation_method or ExtrapolationMethod.FLAT,
            )
        return _Segment(start=float(self.start), end=float(self.end), curve=curve)


@dataclass(frozen=True, slots=True)
class SegmentedCurve(TermStructure):
    """Curve assembled from disjoint tenor segments."""

    _reference_date: Date
    _segments: tuple[_Segment, ...]
    _value_type: ValueType

    def __init__(
        self,
        reference_date: Date,
        segments: Sequence[SegmentBuilder | _Segment],
        *,
        value_type: ValueType,
    ) -> None:
        """Construct a segmented curve from builders or prebuilt segments."""
        built: list[_Segment] = []
        for segment in segments:
            if isinstance(segment, SegmentBuilder):
                built.append(segment.build(reference_date=reference_date, default_value_type=value_type))
            else:
                built.append(segment)
        if not built:
            raise InvalidCurveInput("SegmentedCurve requires at least one segment.")
        built.sort(key=lambda item: item.start)
        for index in range(1, len(built)):
            if built[index].start < built[index - 1].start:
                raise InvalidCurveInput("Segments must be sorted by start tenor.")
        object.__setattr__(self, "_reference_date", reference_date)
        object.__setattr__(self, "_segments", tuple(built))
        object.__setattr__(self, "_value_type", value_type)

    def reference_date(self) -> Date:
        """Return the curve reference date."""
        return self._reference_date

    def tenor_bounds(self) -> tuple[float, float]:
        """Return the outer tenor bounds spanned by the segments."""
        return self._segments[0].start, self._segments[-1].end

    def value_type(self) -> ValueType:
        """Return the common value type of the segmented curve."""
        return self._value_type

    def max_date(self) -> Date:
        """Return the maximum date implied by the final segment."""
        return self.tenor_to_date(self._segments[-1].end)

    def _segment_for(self, tenor: float) -> _Segment:
        for segment in self._segments:
            if segment.contains(tenor):
                return segment
        if tenor < self._segments[0].start:
            return self._segments[0]
        return self._segments[-1]

    def value_at(self, t: float) -> float:
        """Return the value from the segment containing tenor ``t``."""
        tenor = float(t)
        segment = self._segment_for(tenor)
        return float(segment.curve.value_at(tenor))

    def derivative_at(self, t: float) -> float | None:
        """Return the derivative from the selected segment, if available."""
        tenor = float(t)
        segment = self._segment_for(tenor)
        return segment.curve.derivative_at(tenor)

    @property
    def segments(self) -> tuple[_Segment, ...]:
        """Return the immutable tuple of curve segments."""
        return self._segments


__all__ = ["SegmentBuilder", "SegmentSource", "SegmentedCurve"]
