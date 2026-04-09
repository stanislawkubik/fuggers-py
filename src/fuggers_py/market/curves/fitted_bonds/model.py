"""Bond-curve shapes and typed calibration records.

This module defines the supported yield-curve shapes used by the bond-curve
calibration path and the typed result records attached to the fitted curve.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Sequence

import numpy as np
from numpy.typing import NDArray

from fuggers_py.core.types import Date
from fuggers_py.core.ids import InstrumentId
from fuggers_py.market.curves.curve_metadata import CurveDiagnostics
from fuggers_py.market.curves.errors import InvalidCurveInput
from fuggers_py.market.curves.term_structure import TermStructure
from fuggers_py.market.curves.value_type import ValueType
from fuggers_py.products.bonds.traits import Bond
from fuggers_py.reference.reference_data import BondReferenceData

from ._splines import NaturalCubicSplineGrid, cached_natural_cubic_spline_grid


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _decimal_tuple(values: NDArray[np.float64] | tuple[float, ...] | list[float]) -> tuple[Decimal, ...]:
    return tuple(Decimal(str(float(value))) for value in values)


class FittedBondCurveFamily(str, Enum):
    """Supported fitted-bond curve families."""

    EXPONENTIAL_SPLINE = "EXPONENTIAL_SPLINE"
    CUBIC_SPLINE_ZERO_RATE = "CUBIC_SPLINE_ZERO_RATE"


@dataclass(frozen=True, slots=True)
class BondCurveDiagnostics(CurveDiagnostics):
    """Summary diagnostics for a calibrated bond curve.

    The diagnostics record solver convergence, fit size, and weighted residual
    measures in both price and basis-point space so users can judge fit quality
    without recomputing the objective.
    """
    curve_parameter_count: int
    regression_parameter_count: int
    weighted_rmse_price: Decimal
    weighted_mae_price: Decimal
    max_abs_price_residual: Decimal
    weighted_mean_abs_bp_residual: Decimal
    max_abs_bp_residual: Decimal


@dataclass(frozen=True, slots=True)
class BondCurvePoint:
    """One fitted bond point attached to a calibrated bond curve.

    The object is also mapping-like so the existing RV helpers can index it by
    field name while the main code stays typed.
    """

    instrument_id: InstrumentId
    bond: Bond
    maturity_date: Date
    maturity_years: Decimal
    coupon_rate: Decimal | None
    weight: Decimal
    observed_clean_price: Decimal
    observed_dirty_price: Decimal
    observed_yield: Decimal
    curve_clean_price: Decimal
    curve_dirty_price: Decimal
    fitted_clean_price: Decimal
    fitted_dirty_price: Decimal
    fitted_yield: Decimal
    fair_value_clean_price: Decimal
    fair_value_dirty_price: Decimal
    regression_adjustment: Decimal
    price_residual: Decimal
    bp_residual: Decimal
    reference_data: BondReferenceData | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))

    def __getitem__(self, key: str) -> object:
        return getattr(self, key)

    def get(self, key: str, default: object | None = None) -> object | None:
        return getattr(self, key, default)


def _normalize_spline_knot_tenors(
    knot_tenors: Sequence[Decimal | int | float | str],
    *,
    model_name: str,
) -> tuple[Decimal, ...]:
    normalized = tuple(sorted(_to_decimal(value) for value in knot_tenors))
    if len(normalized) < 2:
        raise ValueError(f"{model_name} requires at least two positive knot tenors.")
    if normalized[0] <= Decimal(0):
        raise ValueError(f"{model_name} knot tenors must be strictly positive.")
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{model_name} knot tenors must be unique.")
    return normalized


def _validate_spline_range(knot_tenors: tuple[Decimal, ...], *, max_t: float, label: str) -> None:
    if float(max_t) > float(knot_tenors[-1]) + 0.25:
        raise InvalidCurveInput(f"{label} knot_tenors must extend to the maximum fitted maturity.")


def _support_knot_array(knot_tenors: tuple[Decimal, ...]) -> NDArray[np.float64]:
    return np.asarray([0.0] + [float(knot) for knot in knot_tenors], dtype=float)


def _cached_spline_grid(knot_tenors: tuple[Decimal, ...]) -> NaturalCubicSplineGrid:
    support_knots = tuple(float(knot) for knot in _support_knot_array(knot_tenors))
    return cached_natural_cubic_spline_grid(support_knots)


@dataclass(frozen=True, slots=True)
class ExponentialSplineZeroRateCurve(TermStructure):
    """Zero-rate curve implied by an exponential spline.

    The term structure stores the continuous zero rate at each tenor. Discount
    factors are derived from that zero rate when the surrounding yield curve
    needs them.
    """

    _value_type = ValueType.continuous_zero()

    _reference_date: Date
    coefficients: NDArray[np.float64]
    decay_factors: NDArray[np.float64]
    max_t: float

    def date(self) -> Date:
        """Return the date of the fitted curve."""
        return self._reference_date

    def value_at_tenor(self, t: float) -> float:
        """Return the continuous zero rate at tenor ``t``."""
        tenor = float(t)
        if tenor <= 0.0:
            return float(self.coefficients[0])
        basis = np.concatenate(([1.0], np.exp(-self.decay_factors * tenor)))
        return float(np.dot(self.coefficients, basis))

    def zero_rate_at_tenor(self, t: float) -> float:
        """Return the continuous zero rate at tenor ``t``."""

        return self.value_at_tenor(t)

    def discount_factor_at_tenor(self, t: float) -> float:
        """Return the discount factor implied by the zero rate at tenor ``t``."""

        tenor = float(t)
        if tenor <= 0.0:
            return 1.0
        zero_rate = self.value_at_tenor(tenor)
        return float(np.exp(np.clip(-tenor * zero_rate, -700.0, 700.0)))


@dataclass(frozen=True, slots=True)
class CubicSplineZeroRateCurve(TermStructure):
    """Zero-rate cubic spline used by preferred fitted-bond spline fits.

    The curve stores continuously compounded zero rates on a natural cubic
    spline grid and derives discount factors analytically from those zero
    rates.
    """

    _value_type = ValueType.continuous_zero()

    _reference_date: Date
    knot_tenors: NDArray[np.float64]
    zero_rates: NDArray[np.float64]
    _node_zero_rates: NDArray[np.float64]
    _second_derivatives: NDArray[np.float64]
    _spline_grid: NaturalCubicSplineGrid
    max_t: float

    def date(self) -> Date:
        """Return the date of the fitted curve."""
        return self._reference_date

    def zero_rate_at_tenor(self, t: float) -> float:
        """Return the spline zero rate at tenor ``t``."""

        tenor = float(t)
        if tenor <= 0.0:
            return float(self._node_zero_rates[0])
        return self._spline_grid.evaluate(
            self._node_zero_rates,
            self._second_derivatives,
            tenor,
        )

    def zero_rate_at_date(self, date: Date) -> float:
        """Return the spline zero rate at ``date``."""

        return self.zero_rate_at_tenor(self.date_to_tenor(date))

    def discount_factor_at_tenor(self, t: float) -> float:
        """Return the discount factor implied by the zero rate at tenor ``t``."""

        tenor = float(t)
        if tenor <= 0.0:
            return 1.0
        zero_rate = self.zero_rate_at_tenor(tenor)
        exponent = np.clip(-tenor * zero_rate, -700.0, 700.0)
        return float(np.exp(exponent))

    def discount_factor_at_date(self, date: Date) -> float:
        """Return the discount factor implied by the zero rate at ``date``."""

        return self.discount_factor_at_tenor(self.date_to_tenor(date))

    def value_at_tenor(self, t: float) -> float:
        """Return the zero rate at tenor ``t``."""

        return self.zero_rate_at_tenor(t)

    def derivative_at_tenor(self, t: float) -> float | None:
        """Return the spline zero-rate derivative at tenor ``t``."""

        tenor = max(0.0, float(t))
        return self._spline_grid.derivative(
            self._node_zero_rates,
            self._second_derivatives,
            tenor,
        )


@dataclass(frozen=True, slots=True)
class ExponentialSplineCurveModel:
    """Exponential-spline fitted-bond curve model.

    The model fits a continuous zero-rate spline with fixed exponential decay
    factors.

    Parameters
    ----------
    decay_factors
        Positive exponential decay factors that control the spline basis
        functions. Each value may be passed as ``Decimal``, ``int``, ``float``,
        or ``str`` and is normalized to ``Decimal`` internally.
    """

    decay_factors: tuple[Decimal | int | float | str, ...] = (Decimal("0.50"), Decimal("1.50"))
    family: FittedBondCurveFamily = FittedBondCurveFamily.EXPONENTIAL_SPLINE

    def __post_init__(self) -> None:
        normalized = tuple(_to_decimal(value) for value in self.decay_factors)
        if not normalized:
            raise ValueError("ExponentialSplineCurveModel requires at least one decay factor.")
        if any(value <= Decimal(0) for value in normalized):
            raise ValueError("ExponentialSplineCurveModel decay factors must be positive.")
        object.__setattr__(self, "decay_factors", normalized)

    def parameter_names(self) -> tuple[str, ...]:
        """Return the ordered parameter names for the spline coefficients."""
        return ("beta0",) + tuple(f"beta_exp_{index}" for index in range(1, len(self.decay_factors) + 1))

    def initial_parameters(self, *, observed_yields: NDArray[np.float64], max_t: float) -> NDArray[np.float64]:
        """Return a simple starting point derived from the observed yields."""
        if observed_yields.size == 0:
            level = 0.03
        else:
            level = float(np.median(observed_yields))
        initial = np.zeros(len(self.decay_factors) + 1, dtype=float)
        initial[0] = level
        return initial

    def build_term_structure(
        self,
        reference_date: Date,
        parameters: NDArray[np.float64],
        *,
        max_t: float,
    ) -> TermStructure:
        """Build the fitted zero-rate term structure for the supplied parameters."""
        if parameters.size != len(self.decay_factors) + 1:
            raise InvalidCurveInput("Exponential spline parameter length does not match the decay-factor configuration.")
        return ExponentialSplineZeroRateCurve(
            _reference_date=reference_date,
            coefficients=np.asarray(parameters, dtype=float),
            decay_factors=np.asarray([float(value) for value in self.decay_factors], dtype=float),
            max_t=float(max_t),
        )


@dataclass(frozen=True, slots=True)
class CubicSplineZeroRateCurveModel:
    """Preferred fitted-bond cubic spline model in zero-rate space.

    Instruments provide the observations to fit. ``knot_tenors`` define the
    zero-rate parameter grid used by the spline itself. There is one fitted
    zero-rate parameter per knot tenor, and the cubic spline interpolates the
    zero curve between those knot locations.

    Parameters
    ----------
    knot_tenors
        Positive knot locations in year-fraction tenor space. These are not
        rates. Each value may be passed as ``Decimal``, ``int``, ``float``, or
        ``str`` and is normalized to ``Decimal`` internally.
    initial_zero_rates
        Optional starting zero rates at the knot locations, expressed as raw
        decimal rates such as ``0.02`` for 2 percent. Each value may be passed
        as ``Decimal``, ``int``, ``float``, or ``str`` and is normalized to
        ``Decimal`` internally.
    """

    knot_tenors: tuple[Decimal | int | float | str, ...]
    initial_zero_rates: tuple[Decimal | int | float | str, ...] | None = None
    family: FittedBondCurveFamily = FittedBondCurveFamily.CUBIC_SPLINE_ZERO_RATE

    def __post_init__(self) -> None:
        normalized_knots = _normalize_spline_knot_tenors(
            self.knot_tenors,
            model_name="CubicSplineZeroRateCurveModel",
        )
        object.__setattr__(self, "knot_tenors", normalized_knots)
        if self.initial_zero_rates is None:
            return
        normalized_initial = tuple(_to_decimal(value) for value in self.initial_zero_rates)
        if len(normalized_initial) != len(normalized_knots):
            raise ValueError("CubicSplineZeroRateCurveModel initial_zero_rates must match knot_tenors length.")
        object.__setattr__(self, "initial_zero_rates", normalized_initial)

    def parameter_names(self) -> tuple[str, ...]:
        """Return the ordered parameter names for the spline knot zero rates."""
        return tuple(f"zero_rate_{float(knot):.4f}y" for knot in self.knot_tenors)

    def initial_parameters(self, *, observed_yields: NDArray[np.float64], max_t: float) -> NDArray[np.float64]:
        """Return a starting zero-rate vector for the configured knot grid."""

        _validate_spline_range(
            self.knot_tenors,
            max_t=max_t,
            label="Cubic spline zero-rate",
        )
        if self.initial_zero_rates is not None:
            return np.asarray([float(value) for value in self.initial_zero_rates], dtype=float)
        if observed_yields.size == 0:
            level = 0.03
        else:
            level = float(np.median(observed_yields))
        return np.full(len(self.knot_tenors), level, dtype=float)

    def build_term_structure(
        self,
        reference_date: Date,
        parameters: NDArray[np.float64],
        *,
        max_t: float,
    ) -> TermStructure:
        """Build the fitted zero-rate cubic spline term structure."""

        if parameters.size != len(self.knot_tenors):
            raise InvalidCurveInput("Cubic spline zero-rate parameter length does not match knot_tenors.")
        _validate_spline_range(
            self.knot_tenors,
            max_t=max_t,
            label="Cubic spline zero-rate",
        )
        parameter_array = np.asarray(parameters, dtype=float)
        node_zero_rates = np.concatenate(([parameter_array[0]], parameter_array))
        spline_grid = _cached_spline_grid(self.knot_tenors)
        second_derivatives = spline_grid.second_derivatives(node_zero_rates)
        support_max = max(float(max_t), float(self.knot_tenors[-1]))
        return CubicSplineZeroRateCurve(
            _reference_date=reference_date,
            knot_tenors=np.asarray([float(knot) for knot in self.knot_tenors], dtype=float),
            zero_rates=parameter_array,
            _node_zero_rates=node_zero_rates,
            _second_derivatives=second_derivatives,
            _spline_grid=spline_grid,
            max_t=support_max,
        )


__all__ = [
    "BondCurveDiagnostics",
    "BondCurvePoint",
    "CubicSplineZeroRateCurve",
    "CubicSplineZeroRateCurveModel",
    "ExponentialSplineCurveModel",
    "ExponentialSplineZeroRateCurve",
    "FittedBondCurveFamily",
]
