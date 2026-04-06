"""Fitted bond-curve models and immutable result records.

This module defines the fitted-bond research surface: bond quotes are supplied
with enough context to price them directly, curve values are converted to
dirty prices for the fit, and regression adjustments are added on top of the
curve-implied dirty price. Positive price residuals indicate a bond is rich
to the fit, while positive bp residuals indicate the observed yield is above
the fitted yield.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import TYPE_CHECKING, Mapping, Protocol

import numpy as np
from numpy.typing import NDArray

from fuggers_py.pricers.bonds import BondPricer
from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Date, Price
from fuggers_py.core.ids import InstrumentId
from fuggers_py.market.curves.errors import InvalidCurveInput
from fuggers_py.market.curves.term_structure import TermStructure
from fuggers_py.market.curves.value_type import ValueType
from fuggers_py.market.curves.wrappers import RateCurve

from ._splines import NaturalCubicSplineGrid, cached_natural_cubic_spline_grid

if TYPE_CHECKING:
    from .pricing_adapters import BondCurvePricingAdapter


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


class FittedBondObjective(str, Enum):
    """Objective families used by the fitted-bond optimizer."""

    L1 = "L1"
    L2 = "L2"


@dataclass(frozen=True, slots=True)
class BondCurveFitDiagnostics:
    """Summary diagnostics for a fitted-bond optimization.

    The diagnostics record solver convergence, fit size, and weighted residual
    measures in both price and basis-point space so users can judge fit quality
    without recomputing the objective.
    """

    objective_value: Decimal
    iterations: int
    converged: bool
    observation_count: int
    curve_parameter_count: int
    regression_parameter_count: int
    weighted_rmse_price: Decimal
    weighted_mae_price: Decimal
    max_abs_price_residual: Decimal
    weighted_mean_abs_bp_residual: Decimal
    max_abs_bp_residual: Decimal


@dataclass(frozen=True, slots=True)
class FittedBondCurve:
    """Immutable fitted-bond result bundle.

    The bundle contains the fitted curve, the fitted regression coefficient
    map, one result point for each fitted bond, and summary diagnostics for
    the optimizer run.
    """

    reference_date: Date
    curve_family: FittedBondCurveFamily
    objective: FittedBondObjective
    curve: RateCurve
    curve_parameter_names: tuple[str, ...]
    curve_parameters: tuple[Decimal, ...]
    coefficients: Mapping[str, Decimal]
    bonds: tuple[Mapping[str, object], ...]
    diagnostics: BondCurveFitDiagnostics
    pricing_adapter: BondCurvePricingAdapter | None = None
    _bond_index: Mapping[InstrumentId, Mapping[str, object]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        normalized_coefficients: dict[str, Decimal] = {}
        for raw_name, raw_value in self.coefficients.items():
            name = raw_name.strip().lower()
            if not name:
                raise ValueError("FittedBondCurve coefficients must have non-empty names.")
            if name in normalized_coefficients:
                raise ValueError(f"Duplicate fitted-bond coefficient name: {name}.")
            normalized_coefficients[name] = _to_decimal(raw_value)
        object.__setattr__(self, "coefficients", MappingProxyType(normalized_coefficients))
        normalized_bonds: list[Mapping[str, object]] = []
        bond_index: dict[InstrumentId, Mapping[str, object]] = {}
        for raw_bond in self.bonds:
            resolved_bond = dict(raw_bond)
            instrument_id = InstrumentId.parse(resolved_bond["instrument_id"])
            if instrument_id in bond_index:
                raise ValueError(f"Duplicate fitted-bond instrument_id: {instrument_id}.")
            resolved_bond["instrument_id"] = instrument_id
            normalized_row = MappingProxyType(resolved_bond)
            normalized_bonds.append(normalized_row)
            bond_index[instrument_id] = normalized_row
        object.__setattr__(self, "bonds", tuple(normalized_bonds))
        object.__setattr__(self, "_bond_index", MappingProxyType(bond_index))

    def get_bond(self, instrument_id: InstrumentId | str) -> Mapping[str, object]:
        """Return the fitted row mapping for ``instrument_id``.

        Raises ``KeyError`` when the requested instrument was not part of the
        fitted observation set.
        """
        resolved = InstrumentId.parse(instrument_id)
        try:
            return self._bond_index[resolved]
        except KeyError as exc:
            raise KeyError(f"Unknown fitted bond result: {resolved}.") from exc

    def coefficient_map(self) -> dict[str, Decimal]:
        """Return regression coefficients keyed by normalized exposure name."""
        return dict(self.coefficients)

    def richest(self) -> Mapping[str, object]:
        """Return the bond with the largest positive price residual.

        The result is the bond whose observed dirty price sits furthest above
        its fitted fair value.
        """
        return max(
            self.bonds,
            key=lambda item: (_to_decimal(item["price_residual"]), InstrumentId.parse(item["instrument_id"]).as_str()),
        )

    def cheapest(self) -> Mapping[str, object]:
        """Return the bond with the largest positive bp residual.

        The result is the bond whose observed yield sits furthest above its
        fitted yield.
        """
        return max(
            self.bonds,
            key=lambda item: (_to_decimal(item["bp_residual"]), InstrumentId.parse(item["instrument_id"]).as_str()),
        )


class FittedBondCurveModel(Protocol):
    """Protocol for fitted-bond curve model families.

    Implementations define the parameter names, a starting point, and a way to
    build the fitted curve representation from optimized parameters.
    """

    @property
    def family(self) -> FittedBondCurveFamily:
        ...

    def parameter_names(self) -> tuple[str, ...]:
        ...

    def initial_parameters(self, *, observed_yields: NDArray[np.float64], max_t: float) -> NDArray[np.float64]:
        ...

    def build_curve(self, reference_date: Date, parameters: NDArray[np.float64], *, max_t: float) -> RateCurve:
        ...


def _normalize_spline_knot_tenors(
    knot_tenors: tuple[Decimal, ...],
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
class ExponentialSplineDiscountCurve(TermStructure):
    """Discount-factor curve implied by an exponential spline in zero rates.

    The curve is parameterized as a zero-rate spline and then converted back
    into discount factors for pricing and reporting.
    """

    _reference_date: Date
    coefficients: NDArray[np.float64]
    decay_factors: NDArray[np.float64]
    max_t: float

    def reference_date(self) -> Date:
        """Return the reference date of the fitted curve."""
        return self._reference_date

    def value_type(self) -> ValueType:
        """Return discount-factor semantics."""
        return ValueType.discount_factor()

    def tenor_bounds(self) -> tuple[float, float]:
        """Return the supported tenor range."""
        return (0.0, float(self.max_t))

    def value_at(self, t: float) -> float:
        """Return the discount factor at tenor ``t``.

        Tenors at or before the reference date map to a discount factor of 1.
        """
        tenor = float(t)
        if tenor <= 0.0:
            return 1.0
        basis = np.concatenate(([1.0], np.exp(-self.decay_factors * tenor)))
        zero_rate = float(np.dot(self.coefficients, basis))
        return float(np.exp(np.clip(-tenor * zero_rate, -700.0, 700.0)))

    def max_date(self) -> Date:
        """Return the maximum date implied by ``max_t``."""
        return self.tenor_to_date(float(self.max_t))


@dataclass(frozen=True, slots=True)
class CubicSplineZeroRateCurve(TermStructure):
    """Zero-rate cubic spline used by preferred fitted-bond spline fits.

    The curve stores continuously compounded zero rates on a natural cubic
    spline grid and derives discount factors analytically from those zero
    rates.
    """

    _reference_date: Date
    knot_tenors: NDArray[np.float64]
    zero_rates: NDArray[np.float64]
    _node_zero_rates: NDArray[np.float64]
    _second_derivatives: NDArray[np.float64]
    _spline_grid: NaturalCubicSplineGrid
    max_t: float

    def reference_date(self) -> Date:
        """Return the reference date of the fitted curve."""
        return self._reference_date

    def value_type(self) -> ValueType:
        """Return zero-rate semantics under continuous compounding."""
        return ValueType.continuous_zero()

    def tenor_bounds(self) -> tuple[float, float]:
        """Return the supported tenor range."""
        return (0.0, float(self.max_t))

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

    def value_at(self, t: float) -> float:
        """Return the zero rate at tenor ``t``."""

        return self.zero_rate_at_tenor(t)

    def derivative_at(self, t: float) -> float | None:
        """Return the spline zero-rate derivative at tenor ``t``."""

        tenor = max(0.0, float(t))
        return self._spline_grid.derivative(
            self._node_zero_rates,
            self._second_derivatives,
            tenor,
        )

    def max_date(self) -> Date:
        """Return the maximum date implied by ``max_t``."""
        return self.tenor_to_date(float(self.max_t))


@dataclass(frozen=True, slots=True)
class ExponentialSplineCurveModel:
    """Exponential-spline fitted-bond curve model.

    The model fits a zero-rate spline with fixed exponential decay factors and
    then converts the result into a discount-factor curve.
    """

    decay_factors: tuple[Decimal, ...] = (Decimal("0.50"), Decimal("1.50"))
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

    def build_curve(self, reference_date: Date, parameters: NDArray[np.float64], *, max_t: float) -> RateCurve:
        """Build the fitted discount-factor curve for the supplied parameters."""
        if parameters.size != len(self.decay_factors) + 1:
            raise InvalidCurveInput("Exponential spline parameter length does not match the decay-factor configuration.")
        return RateCurve(
            ExponentialSplineDiscountCurve(
                _reference_date=reference_date,
                coefficients=np.asarray(parameters, dtype=float),
                decay_factors=np.asarray([float(value) for value in self.decay_factors], dtype=float),
                max_t=float(max_t),
            )
        )


@dataclass(frozen=True, slots=True)
class CubicSplineZeroRateCurveModel:
    """Preferred fitted-bond cubic spline model in zero-rate space."""

    knot_tenors: tuple[Decimal, ...]
    initial_zero_rates: tuple[Decimal, ...] | None = None
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

    def build_curve(self, reference_date: Date, parameters: NDArray[np.float64], *, max_t: float) -> RateCurve:
        """Build the fitted zero-rate cubic spline curve."""

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
        return RateCurve(
            CubicSplineZeroRateCurve(
                _reference_date=reference_date,
                knot_tenors=np.asarray([float(knot) for knot in self.knot_tenors], dtype=float),
                zero_rates=parameter_array,
                _node_zero_rates=node_zero_rates,
                _second_derivatives=second_derivatives,
                _spline_grid=spline_grid,
                max_t=support_max,
            )
        )


__all__ = [
    "CubicSplineZeroRateCurve",
    "CubicSplineZeroRateCurveModel",
    "BondCurveFitDiagnostics",
    "ExponentialSplineCurveModel",
    "ExponentialSplineDiscountCurve",
    "FittedBondCurveFamily",
    "FittedBondCurveModel",
    "FittedBondCurve",
    "FittedBondObjective",
]
