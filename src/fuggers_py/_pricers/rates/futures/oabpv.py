"""Option-adjusted fair-price and OABPV helpers for government bond futures.

The fair futures price is the baseline CTD-equivalent price less the delivery
option adjustment. OABPV approximates the price sensitivity of that fair value
to a parallel yield shift, scaled to the contract size.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py._pricers.bonds import BondPricer
from fuggers_py._core.ids import InstrumentId
from fuggers_py._products.rates.futures import DeliverableBasket, GovernmentBondFuture

from .delivery_option import DeliveryOptionModel, NoDeliveryOptionModel, _scenario_equivalent_prices


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class FairFuturesPriceResult:
    """Fair futures price and the baseline CTD components."""

    fair_futures_price: Decimal
    baseline_ctd: InstrumentId
    baseline_conversion_factor: Decimal
    baseline_futures_equivalent_price: Decimal
    delivery_option_adjustment: Decimal


def fair_futures_price(
    contract: GovernmentBondFuture,
    basket: DeliverableBasket,
    *,
    delivery_option_model: DeliveryOptionModel | None = None,
    base_yield_shift_bps: object = Decimal(0),
    prefer_published_conversion_factor: bool = True,
    pricer: BondPricer | None = None,
) -> FairFuturesPriceResult:
    """Return the option-adjusted fair futures price."""
    resolved_pricer = pricer or BondPricer()
    model = delivery_option_model or NoDeliveryOptionModel()
    baseline_candidates = _scenario_equivalent_prices(
        contract,
        basket,
        base_yield_shift_bps=base_yield_shift_bps,
        prefer_published_conversion_factor=prefer_published_conversion_factor,
        pricer=resolved_pricer,
    )
    baseline = baseline_candidates[0]
    option_result = model.delivery_option_adjustment(
        contract,
        basket,
        base_yield_shift_bps=base_yield_shift_bps,
        prefer_published_conversion_factor=prefer_published_conversion_factor,
        pricer=resolved_pricer,
    )
    return FairFuturesPriceResult(
        fair_futures_price=baseline.futures_equivalent_price - option_result.delivery_option_adjustment,
        baseline_ctd=baseline.instrument_id,
        baseline_conversion_factor=baseline.conversion_factor,
        baseline_futures_equivalent_price=baseline.futures_equivalent_price,
        delivery_option_adjustment=option_result.delivery_option_adjustment,
    )


def oabpv(
    contract: GovernmentBondFuture,
    basket: DeliverableBasket,
    *,
    delivery_option_model: DeliveryOptionModel | None = None,
    bump_bps: object = Decimal(1),
    prefer_published_conversion_factor: bool = True,
    pricer: BondPricer | None = None,
) -> Decimal:
    """Return the option-adjusted basis point value in currency units.

    The result is the approximate contract value change for a one-basis-point
    parallel yield move. Positive values mean the fair futures price rises when
    yields fall.
    """
    bump = _to_decimal(bump_bps)
    if bump == Decimal(0):
        raise ValueError("oabpv requires a non-zero bump_bps.")
    down = fair_futures_price(
        contract,
        basket,
        delivery_option_model=delivery_option_model,
        base_yield_shift_bps=-bump,
        prefer_published_conversion_factor=prefer_published_conversion_factor,
        pricer=pricer,
    ).fair_futures_price
    up = fair_futures_price(
        contract,
        basket,
        delivery_option_model=delivery_option_model,
        base_yield_shift_bps=bump,
        prefer_published_conversion_factor=prefer_published_conversion_factor,
        pricer=pricer,
    ).fair_futures_price
    return (down - up) * contract.contract_size / (Decimal(200) * bump)


__all__ = ["FairFuturesPriceResult", "fair_futures_price", "oabpv"]
