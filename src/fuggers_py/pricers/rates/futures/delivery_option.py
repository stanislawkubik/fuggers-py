"""Delivery-option interfaces and deterministic CTD-switch models.

The delivery-option adjustment is the expected benefit from being able to
choose the cheapest deliverable at delivery rather than being forced into a
fixed baseline bond.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable

from fuggers_py.pricers.bonds import BondPricer
from fuggers_py.core.ids import InstrumentId
from fuggers_py.products.rates.futures import DeliverableBasket, GovernmentBondFuture

from .conversion_factor import conversion_factor


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class DeliveryOptionScenario:
    """Single delivery-option scenario in basis-point shift terms.

    ``yield_shift_bps`` is the scenario shock in basis points, and the price
    fields are futures-equivalent clean prices used to compare deliverables.
    """

    yield_shift_bps: Decimal
    cheapest_to_deliver: InstrumentId
    forced_baseline_equivalent_price: Decimal
    optimal_equivalent_price: Decimal
    switching_benefit: Decimal
    probability: Decimal | None = None
    scenario_label: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "yield_shift_bps", _to_decimal(self.yield_shift_bps))
        object.__setattr__(self, "cheapest_to_deliver", InstrumentId.parse(self.cheapest_to_deliver))
        object.__setattr__(self, "forced_baseline_equivalent_price", _to_decimal(self.forced_baseline_equivalent_price))
        object.__setattr__(self, "optimal_equivalent_price", _to_decimal(self.optimal_equivalent_price))
        object.__setattr__(self, "switching_benefit", _to_decimal(self.switching_benefit))
        if self.probability is not None:
            object.__setattr__(self, "probability", _to_decimal(self.probability))
        if self.scenario_label is not None:
            object.__setattr__(self, "scenario_label", self.scenario_label.strip())


@dataclass(frozen=True, slots=True)
class DeliveryOptionResult:
    """Aggregate delivery-option result for a contract and basket.

    ``baseline_ctd`` is the cheapest deliverable at the baseline scenario and
    ``delivery_option_adjustment`` is the expected switching benefit.
    """

    baseline_ctd: InstrumentId
    baseline_futures_equivalent_price: Decimal
    delivery_option_adjustment: Decimal
    scenarios: tuple[DeliveryOptionScenario, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "baseline_ctd", InstrumentId.parse(self.baseline_ctd))
        object.__setattr__(self, "baseline_futures_equivalent_price", _to_decimal(self.baseline_futures_equivalent_price))
        object.__setattr__(self, "delivery_option_adjustment", _to_decimal(self.delivery_option_adjustment))


@dataclass(frozen=True, slots=True)
class _ScenarioCandidate:
    """Internal candidate used when ranking deliverables by futures-equivalent price."""

    instrument_id: InstrumentId
    clean_price: Decimal
    conversion_factor: Decimal
    futures_equivalent_price: Decimal


def _scenario_equivalent_prices(
    contract: GovernmentBondFuture,
    basket: DeliverableBasket,
    *,
    base_yield_shift_bps: object = Decimal(0),
    prefer_published_conversion_factor: bool = True,
    pricer: BondPricer | None = None,
) -> tuple[_ScenarioCandidate, ...]:
    """Return basket candidates sorted by futures-equivalent price."""
    resolved_pricer = pricer or BondPricer()
    scenario_candidates: list[_ScenarioCandidate] = []
    delivery_date = contract.resolved_delivery_date()
    shift_bps = _to_decimal(base_yield_shift_bps)
    for deliverable in basket.deliverables:
        clean_price = deliverable.price_with_yield_shift(
            delivery_date,
            base_settlement_date=basket.as_of,
            yield_shift_bps=shift_bps,
            pricer=resolved_pricer,
        )
        cf = conversion_factor(
            contract,
            deliverable,
            prefer_published_override=prefer_published_conversion_factor,
            pricer=resolved_pricer,
        ).conversion_factor
        scenario_candidates.append(
            _ScenarioCandidate(
                instrument_id=deliverable.instrument_id,
                clean_price=clean_price,
                conversion_factor=cf,
                futures_equivalent_price=clean_price / cf,
            )
        )
    return tuple(sorted(scenario_candidates, key=lambda item: (item.futures_equivalent_price, item.instrument_id.as_str())))


@runtime_checkable
class DeliveryOptionModel(Protocol):
    """Protocol for deterministic delivery-option adjustment models.

    Implementations return the baseline CTD, the baseline futures-equivalent
    price, and the expected delivery-option adjustment for a contract and
    basket.
    """

    def delivery_option_adjustment(
        self,
        contract: GovernmentBondFuture,
        basket: DeliverableBasket,
        *,
        base_yield_shift_bps: object = Decimal(0),
        prefer_published_conversion_factor: bool = True,
        pricer: BondPricer | None = None,
    ) -> DeliveryOptionResult:
        ...


@dataclass(frozen=True, slots=True)
class NoDeliveryOptionModel:
    """Delivery-option model that sets the adjustment to zero."""

    def delivery_option_adjustment(
        self,
        contract: GovernmentBondFuture,
        basket: DeliverableBasket,
        *,
        base_yield_shift_bps: object = Decimal(0),
        prefer_published_conversion_factor: bool = True,
        pricer: BondPricer | None = None,
    ) -> DeliveryOptionResult:
        baseline_candidates = _scenario_equivalent_prices(
            contract,
            basket,
            base_yield_shift_bps=base_yield_shift_bps,
            prefer_published_conversion_factor=prefer_published_conversion_factor,
            pricer=pricer,
        )
        baseline = baseline_candidates[0]
        return DeliveryOptionResult(
            baseline_ctd=baseline.instrument_id,
            baseline_futures_equivalent_price=baseline.futures_equivalent_price,
            delivery_option_adjustment=Decimal(0),
            scenarios=(),
        )


@dataclass(frozen=True, slots=True)
class YieldGridCTDSwitchModel:
    """Delivery-option model based on discrete parallel yield shifts.

    The model averages CTD switching benefit across the configured yield-shift
    grid.
    """

    yield_shifts_bps: tuple[Decimal, ...] = (Decimal("-50"), Decimal("0"), Decimal("50"))

    def __post_init__(self) -> None:
        normalized = tuple(sorted({_to_decimal(item) for item in self.yield_shifts_bps}))
        if not normalized:
            raise ValueError("YieldGridCTDSwitchModel requires at least one yield shift.")
        object.__setattr__(self, "yield_shifts_bps", normalized)

    def delivery_option_adjustment(
        self,
        contract: GovernmentBondFuture,
        basket: DeliverableBasket,
        *,
        base_yield_shift_bps: object = Decimal(0),
        prefer_published_conversion_factor: bool = True,
        pricer: BondPricer | None = None,
    ) -> DeliveryOptionResult:
        """Return the average CTD-switch benefit across the configured grid.

        The result is expressed as a futures-equivalent price adjustment.
        """
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
        scenarios: list[DeliveryOptionScenario] = []
        scenario_probability = Decimal(1) / Decimal(len(self.yield_shifts_bps))
        for yield_shift_bps in self.yield_shifts_bps:
            scenario_candidates = _scenario_equivalent_prices(
                contract,
                basket,
                base_yield_shift_bps=base_shift + yield_shift_bps,
                prefer_published_conversion_factor=prefer_published_conversion_factor,
                pricer=resolved_pricer,
            )
            forced_baseline = next(
                item for item in scenario_candidates if item.instrument_id == baseline.instrument_id
            )
            optimal = scenario_candidates[0]
            switching_benefit = forced_baseline.futures_equivalent_price - optimal.futures_equivalent_price
            if switching_benefit < Decimal(0):
                switching_benefit = Decimal(0)
            scenarios.append(
                DeliveryOptionScenario(
                    yield_shift_bps=yield_shift_bps,
                    cheapest_to_deliver=optimal.instrument_id,
                    forced_baseline_equivalent_price=forced_baseline.futures_equivalent_price,
                    optimal_equivalent_price=optimal.futures_equivalent_price,
                    switching_benefit=switching_benefit,
                    probability=scenario_probability,
                    scenario_label=f"parallel_shift_{yield_shift_bps}",
                )
            )
        adjustment = sum((scenario.switching_benefit for scenario in scenarios), start=Decimal(0)) / Decimal(len(scenarios))
        return DeliveryOptionResult(
            baseline_ctd=baseline.instrument_id,
            baseline_futures_equivalent_price=baseline.futures_equivalent_price,
            delivery_option_adjustment=adjustment,
            scenarios=tuple(scenarios),
        )


__all__ = [
    "DeliveryOptionModel",
    "DeliveryOptionResult",
    "DeliveryOptionScenario",
    "NoDeliveryOptionModel",
    "YieldGridCTDSwitchModel",
]
