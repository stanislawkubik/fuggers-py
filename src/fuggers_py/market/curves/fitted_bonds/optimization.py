"""Optimization entry points for fitted bond curves.

The fitter optimizes curve parameters against dirty-price bond quotes while
profiling additive regression coefficients out of the curve search whenever
named regression exposures are supplied. Residuals are computed in dirty
price, while the reported ``bp_residual`` uses
``(observed_yield - fitted_yield) * 10000``.
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
from fuggers_py.market.curves.wrappers import RateCurve
from fuggers_py.products.bonds.traits import Bond
from fuggers_py.reference.reference_data import BondReferenceData

from .model import (
    BondCurveFitDiagnostics,
    ExponentialSplineCurveModel,
    FittedBondCurveModel,
    FittedBondCurve,
    FittedBondObjective,
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
    raise TypeError("FittedBondCurveFitter reference_date must be a Date or ISO date string.")


def _normalized_bonds(bonds: Mapping[InstrumentId | str, Bond]) -> dict[InstrumentId, Bond]:
    return {InstrumentId.parse(instrument_id): bond for instrument_id, bond in bonds.items()}


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


def _resolve_settlement_date(
    settlement_date: Date | str | None,
    *,
    quotes: Sequence[BondQuote],
) -> Date:
    if settlement_date is not None:
        return Date.parse(settlement_date) if isinstance(settlement_date, str) else settlement_date
    if quotes[0].as_of is None:
        raise ValueError("FittedBondCurveFitter requires settlement_date or BondQuote.as_of.")
    resolved = quotes[0].as_of
    for quote in quotes:
        if quote.as_of is None:
            raise ValueError("FittedBondCurveFitter requires settlement_date or BondQuote.as_of.")
        if quote.as_of != resolved:
            raise ValueError("FittedBondCurveFitter requires a common settlement/reference date.")
    return resolved


def _resolve_bond(quote: BondQuote, *, bonds: Mapping[InstrumentId, Bond]) -> Bond:
    instrument_id = InstrumentId.parse(quote.instrument_id)
    try:
        bond = bonds[instrument_id]
    except KeyError as exc:
        raise KeyError(f"Missing bond definition for fitted quote: {instrument_id}.") from exc
    bond_instrument_id = getattr(bond, "instrument_id", None)
    if bond_instrument_id is not None and InstrumentId.parse(bond_instrument_id) != instrument_id:
        raise ValueError("Bond definition instrument_id must match BondQuote.instrument_id.")
    return bond


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


def _maturity_date(bond: Bond) -> Date:
    return bond.maturity_date()


def _maturity_years(bond: Bond, *, settlement_date: Date) -> Decimal:
    return Decimal(
        str(
            DayCountConvention.ACT_365_FIXED.to_day_count().year_fraction(
                settlement_date,
                _maturity_date(bond),
            )
        )
    )


def _coupon_rate(bond: Bond) -> Decimal | None:
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
    curve: RateCurve
    curve_dirty: NDArray[np.float64]
    coefficients: NDArray[np.float64]
    fair_dirty: NDArray[np.float64]
    residuals: NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class FittedBondCurveFitter:
    """Fit a fitted-bond curve model to cross-sectional bond quotes."""

    curve_model: FittedBondCurveModel = ExponentialSplineCurveModel()
    pricing_adapter: BondCurvePricingAdapter | None = None
    objective: FittedBondObjective = FittedBondObjective.L2
    use_observation_weights: bool = True
    optimization: OptimizationConfig = OptimizationConfig()
    reference_date: object | None = None

    def _resolved_pricing_adapter(self) -> BondCurvePricingAdapter:
        if self.pricing_adapter is not None:
            return self.pricing_adapter
        return NominalGovernmentBondPricingAdapter()

    def _resolved_objective(self) -> FittedBondObjective:
        return self.objective

    def _resolved_optimization(self) -> OptimizationConfig:
        return self.optimization

    def _resolved_use_observation_weights(self) -> bool:
        return self.use_observation_weights

    def fit(
        self,
        quotes: Sequence[BondQuote],
        *,
        bonds: Mapping[InstrumentId | str, Bond],
        settlement_date: Date | str | None = None,
        weights: Mapping[InstrumentId | str, object] | None = None,
        reference_data: Mapping[InstrumentId | str, BondReferenceData] | None = None,
        regression_exposures: Mapping[str, Sequence[object]] | None = None,
    ) -> FittedBondCurve:
        """Fit the curve model and optional regression coefficients.

        The fitter takes raw bond quotes plus a bond lookup keyed by
        ``instrument_id``. Quotes must share one settlement date. Named
        regression exposures are optional additive overlays in dirty-price
        space.
        """

        quote_list = tuple(quotes)
        if not quote_list:
            raise ValueError("FittedBondCurveFitter requires at least one quote.")

        resolved_settlement_date = _resolve_settlement_date(settlement_date, quotes=quote_list)
        reference_date = _resolve_reference_date(self.reference_date, fallback=resolved_settlement_date)
        if reference_date != resolved_settlement_date:
            raise ValueError("FittedBondCurveFitter requires reference_date to match the settlement date.")

        resolved_bonds = _normalized_bonds(bonds)
        resolved_reference_data = _normalized_reference_data(reference_data)
        resolved_weights = _normalized_weights(weights)
        bond_list = tuple(_resolve_bond(quote, bonds=resolved_bonds) for quote in quote_list)
        reference_data_list = tuple(
            _resolve_reference_record(quote, reference_data=resolved_reference_data)
            for quote in quote_list
        )
        quote_weights = tuple(resolved_weights.get(InstrumentId.parse(quote.instrument_id), Decimal(1)) for quote in quote_list)

        pricing_adapter = self._resolved_pricing_adapter()
        objective = self._resolved_objective()
        optimization = self._resolved_optimization()
        use_observation_weights = self._resolved_use_observation_weights()
        variable_names, x_matrix = build_regression_matrix(
            len(quote_list),
            regression_exposures=regression_exposures,
        )
        if use_observation_weights:
            weights = np.asarray(
                [float(weight) for weight in quote_weights],
                dtype=float,
            )
        else:
            weights = np.ones(len(quote_list), dtype=float)
        if np.any(weights <= 0.0):
            raise ValueError("FittedBondCurveFitter weights must be positive.")

        observed_dirty = np.asarray(
            [
                float(
                    pricing_adapter.observed_dirty_price(
                        quote,
                        bond=bond,
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
                    pricing_adapter.observed_yield(
                        quote,
                        bond=bond,
                        settlement_date=resolved_settlement_date,
                    )
                )
                for quote, bond in zip(quote_list, bond_list, strict=True)
            ],
            dtype=float,
        )
        max_t = max(float(_maturity_years(bond, settlement_date=resolved_settlement_date)) for bond in bond_list)

        initial_curve = self.curve_model.initial_parameters(observed_yields=observed_yields, max_t=max_t)

        def _profiled_curve(
            curve_parameters: NDArray[np.float64],
            *,
            regression_weights: NDArray[np.float64],
        ) -> _ProfiledCurveEvaluation:
            curve = self.curve_model.build_curve(reference_date, curve_parameters, max_t=max_t)
            curve_dirty = np.asarray(
                [
                    float(
                        pricing_adapter.curve_dirty_price(
                            quote,
                            curve,
                            bond=bond,
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
                curve=curve,
                curve_dirty=curve_dirty,
                coefficients=coefficient_vector,
                fair_dirty=fair_dirty,
                residuals=residuals,
            )

        if objective is FittedBondObjective.L2:

            def residuals_fn(curve_parameters: NDArray[np.float64]) -> NDArray[np.float64]:
                profiled = _profiled_curve(curve_parameters, regression_weights=weights)
                return np.asarray(np.sqrt(weights) * profiled.residuals, dtype=float)

            optimization_result = levenberg_marquardt(
                residuals_fn,
                initial_curve,
                config=optimization,
            )
            final_profile = _profiled_curve(optimization_result.parameters, regression_weights=weights)
        else:
            epsilon = max(optimization.step_size, 1e-4)
            current_curve = np.asarray(initial_curve, dtype=float)
            current_profile = _profiled_curve(current_curve, regression_weights=weights)
            converged = False
            total_iterations = 0
            objective_value = float(np.sum(weights * np.abs(current_profile.residuals)))
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
                combined_weights = np.asarray(weights * robust_weights, dtype=float)

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
                new_objective_value = float(np.sum(weights * np.abs(new_profile.residuals)))
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

        point_results: list[dict[str, object]] = []
        price_residuals: list[float] = []
        bp_residuals: list[float] = []

        for index, (quote, bond, reference_record) in enumerate(zip(quote_list, bond_list, reference_data_list, strict=True)):
            instrument_id = InstrumentId.parse(quote.instrument_id)
            observed_dirty_price = pricing_adapter.observed_dirty_price(
                quote,
                bond=bond,
                settlement_date=resolved_settlement_date,
            )
            observed_clean_price = pricing_adapter.observed_clean_price(
                quote,
                bond=bond,
                settlement_date=resolved_settlement_date,
            )
            curve_dirty_price = Decimal(str(final_profile.curve_dirty[index]))
            accrued_interest = observed_dirty_price - observed_clean_price
            curve_clean_price = curve_dirty_price - accrued_interest
            fair_dirty_price = Decimal(str(final_profile.fair_dirty[index]))
            fair_clean_price = fair_dirty_price - accrued_interest
            observed_yield = pricing_adapter.observed_yield(
                quote,
                bond=bond,
                settlement_date=resolved_settlement_date,
            )
            fitted_yield = pricing_adapter.fitted_yield(
                quote,
                fair_clean_price,
                final_profile.curve,
                bond=bond,
                settlement_date=resolved_settlement_date,
            )
            regression_adjustment = fair_dirty_price - curve_dirty_price
            price_residual = observed_dirty_price - fair_dirty_price
            bp_residual = (observed_yield - fitted_yield) * Decimal("10000")
            price_residuals.append(float(price_residual))
            bp_residuals.append(float(bp_residual))
            point_results.append(
                {
                    "instrument_id": instrument_id,
                    "bond": bond,
                    "maturity_date": _maturity_date(bond),
                    "maturity_years": _maturity_years(bond, settlement_date=resolved_settlement_date),
                    "coupon_rate": _coupon_rate(bond),
                    "weight": Decimal(str(float(weights[index]))),
                    "observed_clean_price": observed_clean_price,
                    "observed_dirty_price": observed_dirty_price,
                    "observed_yield": observed_yield,
                    "curve_clean_price": curve_clean_price,
                    "curve_dirty_price": curve_dirty_price,
                    "fitted_clean_price": fair_clean_price,
                    "fitted_dirty_price": fair_dirty_price,
                    "fitted_yield": fitted_yield,
                    "fair_value_clean_price": fair_clean_price,
                    "fair_value_dirty_price": fair_dirty_price,
                    "regression_adjustment": regression_adjustment,
                    "price_residual": price_residual,
                    "bp_residual": bp_residual,
                    "reference_data": reference_record,
                }
            )

        weight_sum = float(np.sum(weights))
        weighted_rmse = Decimal(str(float(np.sqrt(np.sum(weights * np.square(price_residuals)) / weight_sum))))
        weighted_mae = Decimal(str(float(np.sum(weights * np.abs(price_residuals)) / weight_sum)))
        weighted_bp_mae = Decimal(str(float(np.sum(weights * np.abs(bp_residuals)) / weight_sum)))
        curve_parameter_count = len(self.curve_model.parameter_names())
        diagnostics = BondCurveFitDiagnostics(
            objective_value=_to_decimal(optimization_result.objective_value),
            iterations=optimization_result.iterations,
            converged=optimization_result.converged,
            observation_count=len(quote_list),
            curve_parameter_count=curve_parameter_count,
            regression_parameter_count=final_profile.coefficients.size,
            weighted_rmse_price=weighted_rmse,
            weighted_mae_price=weighted_mae,
            max_abs_price_residual=Decimal(str(float(np.max(np.abs(price_residuals))))),
            weighted_mean_abs_bp_residual=weighted_bp_mae,
            max_abs_bp_residual=Decimal(str(float(np.max(np.abs(bp_residuals))))),
        )
        return FittedBondCurve(
            reference_date=reference_date,
            curve_family=self.curve_model.family,
            objective=objective,
            curve=final_profile.curve,
            curve_parameter_names=self.curve_model.parameter_names(),
            curve_parameters=tuple(Decimal(str(float(value))) for value in optimization_result.parameters),
            coefficients={
                name: Decimal(str(float(value)))
                for name, value in zip(variable_names, final_profile.coefficients, strict=True)
            },
            bonds=tuple(point_results),
            diagnostics=diagnostics,
            pricing_adapter=pricing_adapter,
        )


__all__ = ["FittedBondCurveFitter"]
