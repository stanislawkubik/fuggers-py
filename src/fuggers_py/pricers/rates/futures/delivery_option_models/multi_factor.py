"""Multi-factor stochastic delivery-option model.

Each scenario supplies factor moves in dimensionless shock units that are
scaled by factor volatilities expressed in basis points and then mapped through
instrument-specific factor loadings.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.pricers.bonds import BondPricer
from fuggers_py.core.ids import InstrumentId
from fuggers_py.products.rates.futures import DeliverableBasket, GovernmentBondFuture

from ..conversion_factor import conversion_factor
from ..delivery_option import DeliveryOptionResult, DeliveryOptionScenario, _scenario_equivalent_prices, _to_decimal


@dataclass(frozen=True, slots=True)
class MultiFactorScenario:
    """Single multi-factor delivery-option scenario."""

    factor_moves: tuple[Decimal, ...]
    probability: Decimal = Decimal(1)
    label: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "factor_moves", tuple(_to_decimal(item) for item in self.factor_moves))
        object.__setattr__(self, "probability", _to_decimal(self.probability))
        if self.probability <= Decimal(0):
            raise ValueError("MultiFactorScenario probability must be positive.")
        if self.label is not None:
            object.__setattr__(self, "label", self.label.strip())


@dataclass(frozen=True, slots=True)
class _ScenarioCandidate:
    """Internal candidate ranked by futures-equivalent price."""

    instrument_id: InstrumentId
    futures_equivalent_price: Decimal


def _normalized_scenarios(scenarios: tuple[MultiFactorScenario, ...]) -> tuple[MultiFactorScenario, ...]:
    """Return scenarios with probabilities normalized to one."""
    total = sum((scenario.probability for scenario in scenarios), start=Decimal(0))
    return tuple(
        MultiFactorScenario(
            factor_moves=scenario.factor_moves,
            probability=scenario.probability / total,
            label=scenario.label,
        )
        for scenario in scenarios
    )


def _scenario_candidates_with_instrument_shifts(
    contract: GovernmentBondFuture,
    basket: DeliverableBasket,
    *,
    yield_shifts_bps: dict[InstrumentId, Decimal],
    prefer_published_conversion_factor: bool,
    pricer: BondPricer,
) -> tuple[_ScenarioCandidate, ...]:
    """Return ranked candidates after applying instrument-specific shifts."""
    delivery_date = contract.resolved_delivery_date()
    candidates: list[_ScenarioCandidate] = []
    for deliverable in basket.deliverables:
        shift = yield_shifts_bps[deliverable.instrument_id]
        clean_price = deliverable.price_with_yield_shift(
            delivery_date,
            base_settlement_date=basket.as_of,
            yield_shift_bps=shift,
            pricer=pricer,
        )
        cf = conversion_factor(
            contract,
            deliverable,
            prefer_published_override=prefer_published_conversion_factor,
            pricer=pricer,
        ).conversion_factor
        candidates.append(
            _ScenarioCandidate(
                instrument_id=deliverable.instrument_id,
                futures_equivalent_price=clean_price / cf,
            )
        )
    return tuple(sorted(candidates, key=lambda item: (item.futures_equivalent_price, item.instrument_id.as_str())))


@dataclass(frozen=True, slots=True)
class MultiFactorDeliveryOptionModel:
    """Delivery-option model driven by multiple factor shocks."""

    factor_volatilities_bps: tuple[Decimal, ...]
    deliverable_factor_loadings: dict[InstrumentId, tuple[Decimal, ...]]
    scenarios: tuple[MultiFactorScenario, ...]
    mean_shift_bps: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        factor_volatilities = tuple(_to_decimal(item) for item in self.factor_volatilities_bps)
        if not factor_volatilities:
            raise ValueError("MultiFactorDeliveryOptionModel requires at least one factor volatility.")
        object.__setattr__(self, "factor_volatilities_bps", factor_volatilities)
        object.__setattr__(self, "mean_shift_bps", _to_decimal(self.mean_shift_bps))
        if not self.scenarios:
            raise ValueError("MultiFactorDeliveryOptionModel requires at least one scenario.")
        normalized_scenarios = tuple(
            scenario if isinstance(scenario, MultiFactorScenario) else MultiFactorScenario(tuple(scenario))  # type: ignore[arg-type]
            for scenario in self.scenarios
        )
        for scenario in normalized_scenarios:
            if len(scenario.factor_moves) != len(factor_volatilities):
                raise ValueError("Each scenario factor_moves tuple must match factor_volatilities_bps length.")
        object.__setattr__(self, "scenarios", _normalized_scenarios(normalized_scenarios))
        normalized_loadings = {
            InstrumentId.parse(key): tuple(_to_decimal(item) for item in value)
            for key, value in self.deliverable_factor_loadings.items()
        }
        for loadings in normalized_loadings.values():
            if len(loadings) != len(factor_volatilities):
                raise ValueError("Each deliverable factor-loading tuple must match factor_volatilities_bps length.")
        object.__setattr__(self, "deliverable_factor_loadings", normalized_loadings)

    def _instrument_shift(
        self,
        instrument_id: InstrumentId,
        *,
        base_shift: Decimal,
        scenario: MultiFactorScenario,
    ) -> Decimal:
        """Return the scenario yield shift for one deliverable."""
        loadings = self.deliverable_factor_loadings.get(instrument_id)
        if loadings is None:
            raise KeyError(f"Missing factor loadings for deliverable {instrument_id}.")
        shift = base_shift + self.mean_shift_bps
        for factor_volatility, factor_move, loading in zip(
            self.factor_volatilities_bps,
            scenario.factor_moves,
            loadings,
            strict=True,
        ):
            shift += factor_volatility * factor_move * loading
        return shift

    def delivery_option_adjustment(
        self,
        contract: GovernmentBondFuture,
        basket: DeliverableBasket,
        *,
        base_yield_shift_bps: object = Decimal(0),
        prefer_published_conversion_factor: bool = True,
        pricer: BondPricer | None = None,
    ) -> DeliveryOptionResult:
        """Return the probability-weighted delivery-option adjustment."""
        resolved_pricer = pricer or BondPricer()
        base_shift = _to_decimal(base_yield_shift_bps)
        baseline_candidates = _scenario_equivalent_prices(
            contract,
            basket,
            base_yield_shift_bps=base_shift,
            prefer_published_conversion_factor=prefer_published_conversion_factor,
            pricer=resolved_pricer,
        )
        baseline = baseline_candidates[0]
        weighted_adjustment = Decimal(0)
        scenarios: list[DeliveryOptionScenario] = []
        for index, scenario in enumerate(self.scenarios):
            shifts = {
                deliverable.instrument_id: self._instrument_shift(
                    deliverable.instrument_id,
                    base_shift=base_shift,
                    scenario=scenario,
                )
                for deliverable in basket.deliverables
            }
            scenario_candidates = _scenario_candidates_with_instrument_shifts(
                contract,
                basket,
                yield_shifts_bps=shifts,
                prefer_published_conversion_factor=prefer_published_conversion_factor,
                pricer=resolved_pricer,
            )
            forced_baseline = next(item for item in scenario_candidates if item.instrument_id == baseline.instrument_id)
            optimal = scenario_candidates[0]
            switching_benefit = max(
                forced_baseline.futures_equivalent_price - optimal.futures_equivalent_price,
                Decimal(0),
            )
            average_shift = sum(shifts.values(), start=Decimal(0)) / Decimal(len(shifts))
            weighted_adjustment += scenario.probability * switching_benefit
            scenarios.append(
                DeliveryOptionScenario(
                    yield_shift_bps=average_shift - base_shift,
                    cheapest_to_deliver=optimal.instrument_id,
                    forced_baseline_equivalent_price=forced_baseline.futures_equivalent_price,
                    optimal_equivalent_price=optimal.futures_equivalent_price,
                    switching_benefit=switching_benefit,
                    probability=scenario.probability,
                    scenario_label=scenario.label or f"multi_factor_{index}",
                )
            )
        return DeliveryOptionResult(
            baseline_ctd=baseline.instrument_id,
            baseline_futures_equivalent_price=baseline.futures_equivalent_price,
            delivery_option_adjustment=weighted_adjustment,
            scenarios=tuple(scenarios),
        )


__all__ = ["MultiFactorDeliveryOptionModel", "MultiFactorScenario"]
