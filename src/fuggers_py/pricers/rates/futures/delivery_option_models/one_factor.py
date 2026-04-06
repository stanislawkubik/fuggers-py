"""One-factor stochastic delivery-option model.

Scenario multipliers are dimensionless shocks applied to the raw-decimal yield
volatility expressed in basis points.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.pricers.bonds import BondPricer
from fuggers_py.products.rates.futures import DeliverableBasket, GovernmentBondFuture

from ..delivery_option import (
    DeliveryOptionResult,
    DeliveryOptionScenario,
    _scenario_equivalent_prices,
    _to_decimal,
)


def _normalize_probabilities(
    probabilities: tuple[Decimal, ...] | None,
    *,
    count: int,
) -> tuple[Decimal, ...]:
    """Normalize scenario probabilities to sum to one."""
    if probabilities is None:
        return tuple(Decimal(1) / Decimal(count) for _ in range(count))
    if len(probabilities) != count:
        raise ValueError("scenario_probabilities must match scenario_multipliers length.")
    total = sum(probabilities, start=Decimal(0))
    if total <= Decimal(0):
        raise ValueError("scenario_probabilities must sum to a positive value.")
    return tuple(item / total for item in probabilities)


@dataclass(frozen=True, slots=True)
class OneFactorDeliveryOptionModel:
    """Parallel-shift delivery-option model with one yield volatility input."""

    yield_volatility_bps: Decimal
    scenario_multipliers: tuple[Decimal, ...] = (Decimal("-1"), Decimal("0"), Decimal("1"))
    scenario_probabilities: tuple[Decimal, ...] | None = None
    mean_shift_bps: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        object.__setattr__(self, "yield_volatility_bps", _to_decimal(self.yield_volatility_bps))
        object.__setattr__(self, "mean_shift_bps", _to_decimal(self.mean_shift_bps))
        multipliers = tuple(_to_decimal(item) for item in self.scenario_multipliers)
        if not multipliers:
            raise ValueError("OneFactorDeliveryOptionModel requires at least one scenario multiplier.")
        object.__setattr__(self, "scenario_multipliers", multipliers)
        if self.scenario_probabilities is not None:
            probabilities = tuple(_to_decimal(item) for item in self.scenario_probabilities)
            object.__setattr__(self, "scenario_probabilities", probabilities)
        if self.yield_volatility_bps < Decimal(0):
            raise ValueError("yield_volatility_bps must be non-negative.")

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
        probabilities = _normalize_probabilities(self.scenario_probabilities, count=len(self.scenario_multipliers))
        baseline_candidates = _scenario_equivalent_prices(
            contract,
            basket,
            base_yield_shift_bps=base_shift,
            prefer_published_conversion_factor=prefer_published_conversion_factor,
            pricer=resolved_pricer,
        )
        baseline = baseline_candidates[0]
        scenarios: list[DeliveryOptionScenario] = []
        weighted_adjustment = Decimal(0)
        for multiplier, probability in zip(self.scenario_multipliers, probabilities, strict=True):
            scenario_shift = base_shift + self.mean_shift_bps + self.yield_volatility_bps * multiplier
            scenario_candidates = _scenario_equivalent_prices(
                contract,
                basket,
                base_yield_shift_bps=scenario_shift,
                prefer_published_conversion_factor=prefer_published_conversion_factor,
                pricer=resolved_pricer,
            )
            forced_baseline = next(item for item in scenario_candidates if item.instrument_id == baseline.instrument_id)
            optimal = scenario_candidates[0]
            switching_benefit = max(
                forced_baseline.futures_equivalent_price - optimal.futures_equivalent_price,
                Decimal(0),
            )
            weighted_adjustment += probability * switching_benefit
            scenarios.append(
                DeliveryOptionScenario(
                    yield_shift_bps=scenario_shift - base_shift,
                    cheapest_to_deliver=optimal.instrument_id,
                    forced_baseline_equivalent_price=forced_baseline.futures_equivalent_price,
                    optimal_equivalent_price=optimal.futures_equivalent_price,
                    switching_benefit=switching_benefit,
                    probability=probability,
                    scenario_label=f"one_factor_{multiplier}",
                )
            )
        return DeliveryOptionResult(
            baseline_ctd=baseline.instrument_id,
            baseline_futures_equivalent_price=baseline.futures_equivalent_price,
            delivery_option_adjustment=weighted_adjustment,
            scenarios=tuple(scenarios),
        )


__all__ = ["OneFactorDeliveryOptionModel"]
