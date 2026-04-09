"""Concrete calibrated nominal bond curve."""

from __future__ import annotations

from decimal import Decimal
from types import MappingProxyType
from typing import Mapping, Sequence

from fuggers_py.core.ids import InstrumentId
from fuggers_py.math.optimization import OptimizationConfig
from fuggers_py.market.quotes import BondQuote
from fuggers_py.reference.reference_data import BondReferenceData

from ..yield_curve import CurveObjective, YieldCurve
from .model import (
    BondCurveDiagnostics,
    BondCurvePoint,
    CubicSplineZeroRateCurveModel,
    ExponentialSplineCurveModel,
    FittedBondCurveFamily,
)
from .optimization import _fit_bond_curve


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class BondCurve(YieldCurve):
    """Concrete calibrated curve built directly from bond quotes.

    This is the public nominal bond-curve object. The curve fits itself from
    bound ``BondQuote`` inputs at construction time and then behaves like a
    yield curve while also exposing the bond-level fit report.
    """

    __slots__ = (
        "_curve_family",
        "_coefficients",
        "_points",
        "_point_index",
        "_pricing_adapter",
    )

    def __init__(
        self,
        quotes: Sequence[BondQuote],
        *,
        shape: ExponentialSplineCurveModel | CubicSplineZeroRateCurveModel = ExponentialSplineCurveModel(),
        objective: CurveObjective = CurveObjective.L2,
        reference_date: object | None = None,
        weights: Mapping[InstrumentId | str, object] | None = None,
        reference_data: Mapping[InstrumentId | str, BondReferenceData] | None = None,
        regressors: Mapping[str, Sequence[object]] | None = None,
        use_observation_weights: bool = True,
        optimization: OptimizationConfig = OptimizationConfig(),
        _pricing_adapter=None,
    ) -> None:
        calibration = _fit_bond_curve(
            quotes,
            shape=shape,
            pricing_adapter=_pricing_adapter,
            objective=objective,
            use_observation_weights=use_observation_weights,
            optimization=optimization,
            reference_date=reference_date,
            weights=weights,
            reference_data=reference_data,
            regressors=regressors,
        )
        super().__init__(
            date=calibration.reference_date,
            term_structure=calibration.term_structure,
            shape=shape,
            objective=objective,
            parameter_names=calibration.parameter_names,
            parameters=calibration.parameters,
            diagnostics=calibration.diagnostics,
        )
        self._curve_family = calibration.curve_family
        self._coefficients = MappingProxyType(dict(calibration.coefficients))
        self._points = calibration.points
        self._point_index = MappingProxyType(
            {InstrumentId.parse(point.instrument_id): point for point in calibration.points}
        )
        self._pricing_adapter = calibration.pricing_adapter

    @property
    def curve_family(self) -> FittedBondCurveFamily:
        return self._curve_family

    @property
    def coefficients(self) -> Mapping[str, Decimal]:
        return self._coefficients

    def coefficient_map(self) -> dict[str, Decimal]:
        return dict(self._coefficients)

    @property
    def bonds(self) -> tuple[BondCurvePoint, ...]:
        return self._points

    @property
    def points(self) -> tuple[BondCurvePoint, ...]:
        return self._points

    @property
    def pricing_adapter(self):
        return self._pricing_adapter

    @property
    def diagnostics(self) -> BondCurveDiagnostics:
        diagnostics = super().diagnostics
        assert isinstance(diagnostics, BondCurveDiagnostics)
        return diagnostics

    def get_bond(self, instrument_id: InstrumentId | str) -> BondCurvePoint:
        resolved = InstrumentId.parse(instrument_id)
        try:
            return self._point_index[resolved]
        except KeyError as exc:
            raise KeyError(f"Unknown bond curve result: {resolved}.") from exc

    def richest(self) -> BondCurvePoint:
        return max(
            self._points,
            key=lambda item: (_to_decimal(item.price_residual), InstrumentId.parse(item.instrument_id).as_str()),
        )

    def cheapest(self) -> BondCurvePoint:
        return max(
            self._points,
            key=lambda item: (_to_decimal(item.bp_residual), InstrumentId.parse(item.instrument_id).as_str()),
        )


__all__ = ["BondCurve"]
