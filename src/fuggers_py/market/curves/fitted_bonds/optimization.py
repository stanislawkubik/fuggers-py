"""Private optimization helpers for calibrated bond curves.

The nominal bond curve and the legacy fitted-bond paths both use the same core
optimization routine. The public bond-curve object owns the resulting
calibration state directly; this module only does the parameter search and
builds the typed point rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, Sequence

import numpy as np
from numpy.typing import NDArray

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.ids import InstrumentId
from fuggers_py.core.types import Date
from fuggers_py.math.optimization import OptimizationConfig, OptimizationResult, levenberg_marquardt
from fuggers_py.market.quotes import BondQuote
from fuggers_py.reference.reference_data import BondReferenceData

from ..curve_metadata import CurveObjective
from ..term_structure import TermStructure
from .model import (
    BondCurveDiagnostics,
    BondCurvePoint,
    CubicSplineZeroRateCurveModel,
    ExponentialSplineCurveModel,
    FittedBondCurveFamily,
)
from .pricing_adapters import BondCurvePricingAdapter, NominalGovernmentBondPricingAdapter
from .regression import build_regression_matrix


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _resolve_reference_date(reference_date: object | None, *, fallback: Date) -> Date:
    if reference_date is None:
        return fallback
    if isinstance(reference_date, Date):
        return reference_date
    if isinstance(reference_date, str):
        return Date.parse(reference_date)
    raise TypeError("BondCurve reference_date must be a Date or ISO date string.")


def _normalized_reference_data(
    reference_data: Mapping[InstrumentId | str, BondReferenceData] | None,
) -> dict[InstrumentId, BondReferenceData]:
    if reference_data is None:
        return {}
    return {InstrumentId.parse(instrument_id): item for instrument_id, item in reference_data.items()}


def _normalized_weights(
    weights: Mapping[InstrumentId | str, object] | None,
) -> dict[InstrumentId, Decimal]:
    if weights is None:
        return {}
    normalized: dict[InstrumentId, Decimal] = {}
    for instrument_id, value in weights.items():
        normalized[InstrumentId.parse(instrument_id)] = _to_decimal(value)
    return normalized


def _resolve_settlement_date(*, quotes: Sequence[BondQuote]) -> Date:
    resolved = quotes[0].resolved_settlement_date()
    for quote in quotes[1:]:
        if quote.resolved_settlement_date() != resolved:
            raise ValueError("BondCurve requires all BondQuote inputs to share one common pricing date.")
    return resolved


def _resolve_reference_record(
    quote: BondQuote,
    *,
    reference_data: Mapping[InstrumentId, BondReferenceData],
) -> BondReferenceData | None:
    instrument_id = InstrumentId.parse(quote.instrument_id)
    record = reference_data.get(instrument_id)
    if record is not None and record.instrument_id != instrument_id:
        raise ValueError("Bond reference_data instrument_id must match BondQuote.instrument_id.")
    return record


def _maturity_date(bond) -> Date:
    return bond.maturity_date()


def _maturity_years(bond, *, settlement_date: Date) -> Decimal:
    return Decimal(
        str(
            DayCountConvention.ACT_365_FIXED.to_day_count().year_fraction(
                settlement_date,
                _maturity_date(bond),
            )
        )
    )


def _coupon_rate(bond) -> Decimal | None:
    coupon_rate = getattr(bond, "coupon_rate", None)
    if callable(coupon_rate):
        return _to_decimal(coupon_rate())
    return None


def _weighted_linear_least_squares(
    x_matrix: NDArray[np.float64],
    target: NDArray[np.float64],
    weights: NDArray[np.float64],
) -> NDArray[np.float64]:
    if x_matrix.shape[1] == 0:
        return np.zeros(0, dtype=float)
    sqrt_weights = np.sqrt(weights)
    weighted_x = sqrt_weights[:, None] * x_matrix
    weighted_target = sqrt_weights * target
    coefficients, _, _, _ = np.linalg.lstsq(weighted_x, weighted_target, rcond=None)
    return np.asarray(coefficients, dtype=float)


@dataclass(frozen=True, slots=True)
class _ProfiledCurveEvaluation:
    term_structure: TermStructure
    curve_dirty: NDArray[np.float64]
    coefficients: NDArray[np.float64]
    fair_dirty: NDArray[np.float64]
    residuals: NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class _BondCurveCalibration:
    reference_date: Date
    curve_family: FittedBondCurveFamily
    term_structure: TermStructure
    parameter_names: tuple[str, ...]
    parameters: tuple[Decimal, ...]
    coefficients: dict[str, Decimal]
    points: tuple[BondCurvePoint, ...]
    diagnostics: BondCurveDiagnostics
    pricing_adapter: BondCurvePricingAdapter


def _fit_bond_curve(
    quotes: Sequence[BondQuote],
    *,
    shape: ExponentialSplineCurveModel | CubicSplineZeroRateCurveModel = ExponentialSplineCurveModel(),
    pricing_adapter: BondCurvePricingAdapter | None = None,
    objective: CurveObjective = CurveObjective.L2,
    use_observation_weights: bool = True,
    optimization: OptimizationConfig = OptimizationConfig(),
    reference_date: object | None = None,
    weights: Mapping[InstrumentId | str, object] | None = None,
    reference_data: Mapping[InstrumentId | str, BondReferenceData] | None = None,
    regressors: Mapping[str, Sequence[object]] | None = None,
) -> _BondCurveCalibration:
    """Fit the curve model and optional regression coefficients."""

    quote_list = tuple(quotes)
    if not quote_list:
        raise ValueError("BondCurve requires at least one quote.")

    resolved_settlement_date = _resolve_settlement_date(quotes=quote_list)
    resolved_reference_date = _resolve_reference_date(reference_date, fallback=resolved_settlement_date)
    if resolved_reference_date != resolved_settlement_date:
        raise ValueError("BondCurve requires reference_date to match the quote pricing date.")

    resolved_reference_data = _normalized_reference_data(reference_data)
    resolved_weights = _normalized_weights(weights)
    bond_list = tuple(quote.instrument for quote in quote_list)
    reference_data_list = tuple(
        _resolve_reference_record(quote, reference_data=resolved_reference_data)
        for quote in quote_list
    )
    quote_weights = tuple(resolved_weights.get(InstrumentId.parse(quote.instrument_id), Decimal(1)) for quote in quote_list)

    resolved_pricing_adapter = pricing_adapter or NominalGovernmentBondPricingAdapter()
    variable_names, x_matrix = build_regression_matrix(
        len(quote_list),
        regression_exposures=regressors,
    )
    if use_observation_weights:
        observation_weights = np.asarray(
            [float(weight) for weight in quote_weights],
            dtype=float,
        )
    else:
        observation_weights = np.ones(len(quote_list), dtype=float)
    if np.any(observation_weights <= 0.0):
        raise ValueError("BondCurve weights must be positive.")

    observed_dirty = np.asarray(
        [
            float(
                resolved_pricing_adapter.observed_dirty_price(
                    quote,
                    settlement_date=resolved_settlement_date,
                )
            )
            for quote, bond in zip(quote_list, bond_list, strict=True)
        ],
        dtype=float,
    )
    observed_yields = np.asarray(
        [
            float(
                resolved_pricing_adapter.observed_yield(
                    quote,
                    settlement_date=resolved_settlement_date,
                )
            )
            for quote, bond in zip(quote_list, bond_list, strict=True)
        ],
        dtype=float,
    )
    max_t = max(float(_maturity_years(bond, settlement_date=resolved_settlement_date)) for bond in bond_list)

    initial_curve = shape.initial_parameters(observed_yields=observed_yields, max_t=max_t)

    def _profiled_curve(
        curve_parameters: NDArray[np.float64],
        *,
        regression_weights: NDArray[np.float64],
    ) -> _ProfiledCurveEvaluation:
        term_structure = shape.build_term_structure(
            resolved_reference_date,
            curve_parameters,
            max_t=max_t,
        )
        curve_dirty = np.asarray(
            [
                float(
                    resolved_pricing_adapter.curve_dirty_price(
                        quote,
                        term_structure,
                        settlement_date=resolved_settlement_date,
                    )
                )
                for quote, bond in zip(quote_list, bond_list, strict=True)
            ],
            dtype=float,
        )
        regression_target = np.asarray(observed_dirty - curve_dirty, dtype=float)
        coefficient_vector = _weighted_linear_least_squares(
            x_matrix,
            regression_target,
            regression_weights,
        )
        regression_adjustment = x_matrix @ coefficient_vector if coefficient_vector.size else np.zeros_like(curve_dirty)
        fair_dirty = np.asarray(curve_dirty + regression_adjustment, dtype=float)
        residuals = np.asarray(fair_dirty - observed_dirty, dtype=float)
        return _ProfiledCurveEvaluation(
            term_structure=term_structure,
            curve_dirty=curve_dirty,
            coefficients=coefficient_vector,
            fair_dirty=fair_dirty,
            residuals=residuals,
        )

    if objective is CurveObjective.L2:

        def residuals_fn(curve_parameters: NDArray[np.float64]) -> NDArray[np.float64]:
            profiled = _profiled_curve(curve_parameters, regression_weights=observation_weights)
            return np.asarray(np.sqrt(observation_weights) * profiled.residuals, dtype=float)

        optimization_result = levenberg_marquardt(
            residuals_fn,
            initial_curve,
            config=optimization,
        )
        final_profile = _profiled_curve(optimization_result.parameters, regression_weights=observation_weights)
    else:
        epsilon = max(optimization.step_size, 1e-4)
        current_curve = np.asarray(initial_curve, dtype=float)
        current_profile = _profiled_curve(current_curve, regression_weights=observation_weights)
        converged = False
        total_iterations = 0
        objective_value = float(np.sum(observation_weights * np.abs(current_profile.residuals)))
        outer_iterations = max(3, min(12, optimization.max_iterations))
        lm_max_iterations = max(5, optimization.max_iterations // outer_iterations)
        lm_config = OptimizationConfig(
            tolerance=optimization.tolerance,
            max_iterations=lm_max_iterations,
            step_size=optimization.step_size,
            armijo_c=optimization.armijo_c,
            backtracking_beta=optimization.backtracking_beta,
            min_step=optimization.min_step,
            lm_initial_damping=optimization.lm_initial_damping,
            lm_damping_increase=optimization.lm_damping_increase,
            lm_damping_decrease=optimization.lm_damping_decrease,
        )
        for _ in range(outer_iterations):
            residual_scale = max(float(np.median(np.abs(current_profile.residuals))), epsilon)
            robust_weights = 1.0 / np.sqrt(np.square(current_profile.residuals) + residual_scale * residual_scale)
            robust_weights = robust_weights / float(np.mean(robust_weights))
            combined_weights = np.asarray(observation_weights * robust_weights, dtype=float)

            def residuals_fn(curve_parameters: NDArray[np.float64]) -> NDArray[np.float64]:
                profiled = _profiled_curve(curve_parameters, regression_weights=combined_weights)
                return np.asarray(np.sqrt(combined_weights) * profiled.residuals, dtype=float)

            lm_result = levenberg_marquardt(
                residuals_fn,
                current_curve,
                config=lm_config,
            )
            total_iterations += lm_result.iterations
            new_profile = _profiled_curve(lm_result.parameters, regression_weights=combined_weights)
            new_objective_value = float(np.sum(observation_weights * np.abs(new_profile.residuals)))
            if abs(new_objective_value - objective_value) <= optimization.tolerance:
                current_curve = lm_result.parameters
                current_profile = new_profile
                objective_value = new_objective_value
                converged = True
                break
            if float(np.linalg.norm(lm_result.parameters - current_curve)) <= optimization.tolerance:
                current_curve = lm_result.parameters
                current_profile = new_profile
                objective_value = new_objective_value
                converged = True
                break
            current_curve = lm_result.parameters
            current_profile = new_profile
            objective_value = new_objective_value

        optimization_result = OptimizationResult(
            parameters=current_curve,
            objective_value=objective_value,
            iterations=total_iterations,
            converged=converged,
        )
        final_profile = current_profile

    point_results: list[BondCurvePoint] = []
    price_residuals: list[float] = []
    bp_residuals: list[float] = []

    for index, (quote, bond, reference_record) in enumerate(zip(quote_list, bond_list, reference_data_list, strict=True)):
        instrument_id = InstrumentId.parse(quote.instrument_id)
        observed_dirty_price = resolved_pricing_adapter.observed_dirty_price(
            quote,
            settlement_date=resolved_settlement_date,
        )
        observed_clean_price = resolved_pricing_adapter.observed_clean_price(
            quote,
            settlement_date=resolved_settlement_date,
        )
        curve_dirty_price = Decimal(str(final_profile.curve_dirty[index]))
        accrued_interest = observed_dirty_price - observed_clean_price
        curve_clean_price = curve_dirty_price - accrued_interest
        fair_dirty_price = Decimal(str(final_profile.fair_dirty[index]))
        fair_clean_price = fair_dirty_price - accrued_interest
        observed_yield = resolved_pricing_adapter.observed_yield(
            quote,
            settlement_date=resolved_settlement_date,
        )
        fitted_yield = resolved_pricing_adapter.fitted_yield(
            quote,
            fair_clean_price,
            final_profile.term_structure,
            settlement_date=resolved_settlement_date,
        )
        regression_adjustment = fair_dirty_price - curve_dirty_price
        price_residual = observed_dirty_price - fair_dirty_price
        bp_residual = (observed_yield - fitted_yield) * Decimal("10000")
        price_residuals.append(float(price_residual))
        bp_residuals.append(float(bp_residual))
        point_results.append(
            BondCurvePoint(
                instrument_id=instrument_id,
                bond=bond,
                maturity_date=_maturity_date(bond),
                maturity_years=_maturity_years(bond, settlement_date=resolved_settlement_date),
                coupon_rate=_coupon_rate(bond),
                weight=Decimal(str(float(observation_weights[index]))),
                observed_clean_price=observed_clean_price,
                observed_dirty_price=observed_dirty_price,
                observed_yield=observed_yield,
                curve_clean_price=curve_clean_price,
                curve_dirty_price=curve_dirty_price,
                fitted_clean_price=fair_clean_price,
                fitted_dirty_price=fair_dirty_price,
                fitted_yield=fitted_yield,
                fair_value_clean_price=fair_clean_price,
                fair_value_dirty_price=fair_dirty_price,
                regression_adjustment=regression_adjustment,
                price_residual=price_residual,
                bp_residual=bp_residual,
                reference_data=reference_record,
            )
        )

    weight_sum = float(np.sum(observation_weights))
    weighted_rmse = Decimal(str(float(np.sqrt(np.sum(observation_weights * np.square(price_residuals)) / weight_sum))))
    weighted_mae = Decimal(str(float(np.sum(observation_weights * np.abs(price_residuals)) / weight_sum)))
    weighted_bp_mae = Decimal(str(float(np.sum(observation_weights * np.abs(bp_residuals)) / weight_sum)))
    curve_parameter_count = len(shape.parameter_names())
    diagnostics = BondCurveDiagnostics(
        objective_value=_to_decimal(optimization_result.objective_value),
        iterations=optimization_result.iterations,
        converged=optimization_result.converged,
        observation_count=len(quote_list),
        parameter_count=curve_parameter_count + final_profile.coefficients.size,
        curve_parameter_count=curve_parameter_count,
        regression_parameter_count=final_profile.coefficients.size,
        weighted_rmse_price=weighted_rmse,
        weighted_mae_price=weighted_mae,
        max_abs_price_residual=Decimal(str(float(np.max(np.abs(price_residuals))))),
        weighted_mean_abs_bp_residual=weighted_bp_mae,
        max_abs_bp_residual=Decimal(str(float(np.max(np.abs(bp_residuals))))),
    )
    return _BondCurveCalibration(
        reference_date=resolved_reference_date,
        curve_family=shape.family,
        term_structure=final_profile.term_structure,
        parameter_names=shape.parameter_names(),
        parameters=tuple(Decimal(str(float(value))) for value in optimization_result.parameters),
        coefficients={
            name: Decimal(str(float(value)))
            for name, value in zip(variable_names, final_profile.coefficients, strict=True)
        },
        points=tuple(point_results),
        diagnostics=diagnostics,
        pricing_adapter=resolved_pricing_adapter,
    )

@dataclass(frozen=True, slots=True)
class BondCurveFitter:
    """Legacy entry point for fitted bond curves.

    The public calibrated-curve API is ``BondCurve(...)``. This class remains
    available while the other bond-curve paths migrate to the new surface.
    """

    curve_model: ExponentialSplineCurveModel | CubicSplineZeroRateCurveModel = ExponentialSplineCurveModel()
    pricing_adapter: BondCurvePricingAdapter | None = None
    objective: CurveObjective = CurveObjective.L2
    use_observation_weights: bool = True
    optimization: OptimizationConfig = OptimizationConfig()
    reference_date: object | None = None

    def fit(
        self,
        quotes: Sequence[BondQuote],
        *,
        weights: Mapping[InstrumentId | str, object] | None = None,
        reference_data: Mapping[InstrumentId | str, BondReferenceData] | None = None,
        regression_exposures: Mapping[str, Sequence[object]] | None = None,
    ):
        from .bond_curve import BondCurve

        return BondCurve(
            quotes,
            shape=self.curve_model,
            objective=self.objective,
            reference_date=self.reference_date,
            weights=weights,
            reference_data=reference_data,
            regressors=regression_exposures,
            use_observation_weights=self.use_observation_weights,
            optimization=self.optimization,
            _pricing_adapter=self.pricing_adapter,
        )


__all__ = ["BondCurveFitter", "_fit_bond_curve"]
