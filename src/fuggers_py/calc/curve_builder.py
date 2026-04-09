"""Small synchronous curve builder for calc-layer workflows.

This is a convenience layer over the curve package and the shared curve-input
records. It is intentionally narrow: it helps build and cache curves for
research and calculation workflows, but it is not the canonical calibration
path. Built curves are cached by identifier together with the inputs used to
create them so the reactive runtime can reuse or inspect them later.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Compounding
from fuggers_py.market.curves import DiscountCurveBuilder, InterpolationMethod
from fuggers_py.market.curves.term_structure import TermStructure
from fuggers_py.market.curves.value_type import ValueType

from fuggers_py.core.ids import CurveId
from fuggers_py.market.snapshot import CurveInputs, CurvePoint
from fuggers_py.calc.pricing_specs import AnalyticsCurves

from .errors import CurveNotFoundError


_INTERPOLATION_MAP = {
    "linear": InterpolationMethod.LINEAR,
    "log_linear": InterpolationMethod.LOG_LINEAR,
    "flat_forward": InterpolationMethod.FLAT_FORWARD,
    "monotone_convex": InterpolationMethod.MONOTONE_CONVEX,
    "cubic_spline": InterpolationMethod.CUBIC_SPLINE,
}


@dataclass(frozen=True, slots=True)
class ForwardRateCurve:
    """Forward-rate view over a zero-rate curve.

    The wrapper keeps the underlying zero-curve object but exposes forward-rate
    accessors for code that expects a forward-curve interface.
    """

    curve: TermStructure

    def date(self):
        """Return the curve date."""
        return self.curve.date()

    def forward_rate_at(self, tenor: float) -> float:
        """Return the zero rate at a tenor using the wrapped curve."""
        return self.curve.zero_rate_at_tenor(float(tenor))

    def forward_rate(self, start, end) -> float:
        """Return the implied forward rate between two dates."""
        reference_date = self.date()
        start_tenor = float(reference_date.days_between(start)) / 365.0
        end_tenor = float(reference_date.days_between(end)) / 365.0
        return self.curve.forward_rate_at_tenors(start_tenor, end_tenor)


@dataclass(frozen=True, slots=True)
class BuiltCurve:
    """Named curve bundle returned by the builder.

    The wrapper preserves the curve identifier, the built curve object itself,
    and the original serialized inputs when available.
    """

    curve_id: CurveId
    curve: object
    curve_inputs: CurveInputs | None = None

    @classmethod
    def of(
        cls,
        curve_id: CurveId | str,
        curve: object,
        *,
        curve_inputs: CurveInputs | None = None,
    ) -> "BuiltCurve":
        """Create a built-curve wrapper from a curve identifier and payload."""
        return cls(curve_id=CurveId.parse(curve_id), curve=curve, curve_inputs=curve_inputs)

    def unwrap(self) -> object:
        """Return the wrapped curve object."""
        return self.curve

    def date(self):
        """Return the curve date when it can be resolved."""
        if hasattr(self.curve, "date"):
            return getattr(self.curve, "date")()
        if self.curve_inputs is not None:
            return self.curve_inputs.reference_date
        return None


@dataclass(frozen=True, slots=True)
class _FlatTermStructure(TermStructure):
    _reference_date: object
    _value: float
    _max_tenor: float
    _value_type: ValueType

    def date(self):
        return self._reference_date

    def value_at_tenor(self, t: float) -> float:
        return self._value


def _curve_key(curve_id: CurveId | str) -> str:
    return curve_id.as_str() if isinstance(curve_id, CurveId) else CurveId.parse(curve_id).as_str()


def _curve_inputs(curve_id: CurveId | str, reference_date, points, interpolation: str, curve_kind: str) -> CurveInputs:
    normalized_points = tuple(sorted(points, key=lambda point: point.tenor))
    return CurveInputs.from_points(
        curve_id=curve_id,
        reference_date=reference_date,
        points=list(normalized_points),
        interpolation=interpolation,
        curve_kind=curve_kind,
    )


def _single_pillar_curve(
    points: list[CurvePoint] | tuple[CurvePoint, ...],
    reference_date,
    *,
    discount_factor: bool,
) -> TermStructure:
    point = sorted(points, key=lambda item: item.tenor)[0]
    value_type = (
        ValueType.discount_factor()
        if discount_factor
        else ValueType.zero_rate(Compounding.CONTINUOUS, DayCountConvention.ACT_365_FIXED)
    )
    return _FlatTermStructure(
        _reference_date=reference_date,
        _value=float(point.value),
        _max_tenor=float(point.tenor),
        _value_type=value_type,
    )


@dataclass(slots=True)
class CurveBuilder:
    """Cache and name curves built from raw market data inputs.

    The builder handles zero, discount, and forward curves. It sorts input
    points by tenor, handles single-pillar curves with a flat term structure,
    and stores the original :class:`CurveInputs` alongside the built result.
    """

    _curves: dict[str, object] = field(default_factory=dict)
    _curve_inputs: dict[str, CurveInputs] = field(default_factory=dict)

    def add_zero_curve(
        self,
        curve_id: CurveId | str,
        points: list[CurvePoint] | tuple[CurvePoint, ...],
        reference_date,
        *,
        interpolation: str = "linear",
    ) -> TermStructure:
        """Build and store a zero curve from raw curve points.

        The input points are sorted by tenor before calibration, and a single
        pillar is turned into a flat term structure so the builder still returns
        a usable curve object.
        """
        builder = DiscountCurveBuilder(reference_date=reference_date)
        method = _INTERPOLATION_MAP.get(interpolation.lower())
        if method is not None:
            builder = builder.with_interpolation(method)
        normalized_points = sorted(points, key=lambda item: item.tenor)
        if len(normalized_points) == 1:
            curve = _single_pillar_curve(normalized_points, reference_date, discount_factor=False)
            key = _curve_key(curve_id)
            self._curves[key] = curve
            self._curve_inputs[key] = _curve_inputs(curve_id, reference_date, normalized_points, interpolation, "zero")
            return curve
        for point in normalized_points:
            builder.add_zero_rate(float(point.tenor), point.value)
        curve = builder.build()
        key = _curve_key(curve_id)
        self._curves[key] = curve
        self._curve_inputs[key] = _curve_inputs(curve_id, reference_date, normalized_points, interpolation, "zero")
        return curve

    def add_discount_curve(
        self,
        curve_id: CurveId | str,
        points: list[CurvePoint] | tuple[CurvePoint, ...],
        reference_date,
        *,
        interpolation: str = "log_linear",
    ) -> TermStructure:
        """Build and store a discount curve from raw curve points.

        The input points are sorted by tenor before calibration, and a single
        pillar is turned into a flat term structure so the builder still returns
        a usable curve object.
        """
        builder = DiscountCurveBuilder(reference_date=reference_date)
        method = _INTERPOLATION_MAP.get(interpolation.lower())
        if method is not None:
            builder = builder.with_interpolation(method)
        normalized_points = sorted(points, key=lambda item: item.tenor)
        if len(normalized_points) == 1:
            curve = _single_pillar_curve(normalized_points, reference_date, discount_factor=True)
            key = _curve_key(curve_id)
            self._curves[key] = curve
            self._curve_inputs[key] = _curve_inputs(curve_id, reference_date, normalized_points, interpolation, "discount")
            return curve
        for point in normalized_points:
            builder.add_pillar(float(point.tenor), point.value)
        curve = builder.build()
        key = _curve_key(curve_id)
        self._curves[key] = curve
        self._curve_inputs[key] = _curve_inputs(curve_id, reference_date, normalized_points, interpolation, "discount")
        return curve

    def add_forward_curve(
        self,
        curve_id: CurveId | str,
        points: list[CurvePoint] | tuple[CurvePoint, ...],
        reference_date,
        *,
        interpolation: str = "linear",
    ) -> ForwardRateCurve:
        """Build and store a forward-rate view over the supplied points.

        The builder first stores the underlying zero curve, then wraps it in a
        forward-rate view so downstream code can query either representation.
        """
        rate_curve = self.add_zero_curve(curve_id, points, reference_date, interpolation=interpolation)
        forward_curve = ForwardRateCurve(rate_curve)
        key = _curve_key(curve_id)
        self._curves[key] = forward_curve
        self._curve_inputs[key] = _curve_inputs(curve_id, reference_date, points, interpolation, "forward")
        return forward_curve

    def add_from_inputs(self, curve_inputs: CurveInputs) -> object:
        """Build a curve from a serialized :class:`~fuggers_py.market.snapshot.CurveInputs` record.

        The `curve_kind` field selects whether the inputs produce a zero,
        discount, or forward curve.
        """
        if curve_inputs.curve_kind == "discount":
            return self.add_discount_curve(
                curve_inputs.curve_id,
                curve_inputs.points,
                curve_inputs.reference_date,
                interpolation=curve_inputs.interpolation,
            )
        if curve_inputs.curve_kind == "forward":
            return self.add_forward_curve(
                curve_inputs.curve_id,
                curve_inputs.points,
                curve_inputs.reference_date,
                interpolation=curve_inputs.interpolation,
            )
        return self.add_zero_curve(
            curve_inputs.curve_id,
            curve_inputs.points,
            curve_inputs.reference_date,
            interpolation=curve_inputs.interpolation,
        )

    def get(self, curve_id: CurveId | str) -> object:
        """Return a previously built curve by identifier."""
        key = _curve_key(curve_id)
        if key not in self._curves:
            raise CurveNotFoundError(f"Curve {key!r} is not available.")
        return self._curves[key]

    def built_curve(self, curve_id: CurveId | str) -> BuiltCurve:
        """Return the curve together with the stored curve-input record."""
        key = _curve_key(curve_id)
        if key not in self._curves:
            raise CurveNotFoundError(f"Curve {key!r} is not available.")
        return BuiltCurve.of(curve_id, self._curves[key], curve_inputs=self._curve_inputs.get(key))

    def inputs_for(self, curve_id: CurveId | str) -> CurveInputs:
        """Return the stored curve inputs for a curve identifier."""
        key = _curve_key(curve_id)
        if key not in self._curve_inputs:
            raise CurveNotFoundError(f"Curve inputs for {key!r} are not available.")
        return self._curve_inputs[key]

    def bundle(
        self,
        *,
        discount_curve: CurveId | str | None = None,
        forward_curve: CurveId | str | None = None,
        government_curve: CurveId | str | None = None,
        benchmark_curve: CurveId | str | None = None,
    ) -> AnalyticsCurves:
        """Return an :class:`AnalyticsCurves` bundle from stored curve names."""
        return AnalyticsCurves(
            discount_curve=None if discount_curve is None else self.get(discount_curve),
            forward_curve=None if forward_curve is None else self.get(forward_curve),
            government_curve=None if government_curve is None else self.get(government_curve),
            benchmark_curve=None if benchmark_curve is None else self.get(benchmark_curve),
        )


__all__ = ["BuiltCurve", "CurveBuilder", "ForwardRateCurve"]
