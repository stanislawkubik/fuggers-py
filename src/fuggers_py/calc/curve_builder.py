"""Calc-layer storage for externally built curves.

Calc no longer constructs curves. The curve module is the only place that owns
curve fitting and curve math. This module only stores finished curves by id and
optionally keeps the raw ``CurveInputs`` records that arrived alongside them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fuggers_py.core.ids import CurveId
from fuggers_py.market.snapshot import CurveInputs
from fuggers_py.calc.pricing_specs import AnalyticsCurves

from .errors import CurveNotFoundError


def _curve_key(curve_id: CurveId | str) -> str:
    return curve_id.as_str() if isinstance(curve_id, CurveId) else CurveId.parse(curve_id).as_str()


@dataclass(frozen=True, slots=True)
class BuiltCurve:
    """Named finished-curve bundle returned by the calc registry."""

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
        return cls(curve_id=CurveId.parse(curve_id), curve=curve, curve_inputs=curve_inputs)

    def unwrap(self) -> object:
        """Return the stored curve object."""

        return self.curve

    def date(self):
        """Return the curve reference date when it can be resolved."""

        if hasattr(self.curve, "reference_date"):
            return getattr(self.curve, "reference_date")
        if hasattr(self.curve, "date"):
            candidate = getattr(self.curve, "date")
            return candidate() if callable(candidate) else candidate
        if self.curve_inputs is not None:
            return self.curve_inputs.reference_date
        return None


@dataclass(slots=True)
class CurveBuilder:
    """Small calc-layer registry for finished curves and raw inputs.

    The historical name is kept for API continuity, but this object no longer
    builds curves. Callers must construct curves in ``market.curves`` and then
    store them here.
    """

    _curves: dict[str, object] = field(default_factory=dict)
    _curve_inputs: dict[str, CurveInputs] = field(default_factory=dict)

    def add_curve(
        self,
        curve_id: CurveId | str,
        curve: object,
        *,
        curve_inputs: CurveInputs | None = None,
    ) -> object:
        """Store one externally built curve under ``curve_id``."""

        if curve is None:
            raise ValueError("curve must be a built curve object, not None.")
        key = _curve_key(curve_id)
        if curve_inputs is not None and curve_inputs.curve_id.as_str() != key:
            raise ValueError("curve_inputs.curve_id must match curve_id.")
        self._curves[key] = curve
        if curve_inputs is not None:
            self._curve_inputs[key] = curve_inputs
        return curve

    def add_from_inputs(self, curve_inputs: CurveInputs) -> CurveInputs:
        """Store raw curve inputs without building a curve from them."""

        key = _curve_key(curve_inputs.curve_id)
        self._curve_inputs[key] = curve_inputs
        return curve_inputs

    def get(self, curve_id: CurveId | str) -> object:
        """Return a stored finished curve by identifier."""

        key = _curve_key(curve_id)
        if key not in self._curves:
            raise CurveNotFoundError(f"Curve {key!r} is not available.")
        return self._curves[key]

    def built_curve(self, curve_id: CurveId | str) -> BuiltCurve:
        """Return the stored curve together with any remembered inputs."""

        key = _curve_key(curve_id)
        if key not in self._curves:
            raise CurveNotFoundError(f"Curve {key!r} is not available.")
        return BuiltCurve.of(curve_id, self._curves[key], curve_inputs=self._curve_inputs.get(key))

    def inputs_for(self, curve_id: CurveId | str) -> CurveInputs:
        """Return the stored raw inputs for ``curve_id``."""

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
        """Return an ``AnalyticsCurves`` bundle from stored curve names."""

        return AnalyticsCurves(
            discount_curve=None if discount_curve is None else self.get(discount_curve),
            forward_curve=None if forward_curve is None else self.get(forward_curve),
            government_curve=None if government_curve is None else self.get(government_curve),
            benchmark_curve=None if benchmark_curve is None else self.get(benchmark_curve),
        )


__all__ = ["BuiltCurve", "CurveBuilder"]
