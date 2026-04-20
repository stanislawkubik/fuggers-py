"""Cheapest-to-deliver helpers for government bond futures.

Notes
-----
``delivery_payoff`` is defined as
``futures_price * conversion_factor - cash_clean_price``.
The short prefers the largest delivery payoff, which is equivalent to the
smallest gross basis.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py._core.ids import InstrumentId
from fuggers_py._products.rates.futures import DeliverableBasket, GovernmentBondFuture

from .basis import gross_basis
from .conversion_factor import conversion_factor


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class DeliverableCandidate:
    """Candidate deliverable bond ranked for CTD selection."""

    instrument_id: InstrumentId
    clean_price: Decimal
    conversion_factor: Decimal
    futures_equivalent_price: Decimal
    delivery_payoff: Decimal
    gross_basis: Decimal


@dataclass(frozen=True, slots=True)
class CheapestToDeliverResult:
    """CTD ranking for a futures contract and deliverable basket."""

    futures_price: Decimal
    cheapest_to_deliver: InstrumentId
    conversion_factor: Decimal
    gross_basis: Decimal
    delivery_payoff: Decimal
    candidates: tuple[DeliverableCandidate, ...]


def delivery_payoff(futures_price: object, conversion_factor: object, clean_price: object) -> Decimal:
    """Return the short's delivery payoff in percent of par."""
    return _to_decimal(futures_price) * _to_decimal(conversion_factor) - _to_decimal(clean_price)


def cheapest_to_deliver(
    contract: GovernmentBondFuture,
    basket: DeliverableBasket,
    futures_price: object,
    *,
    prefer_published_conversion_factor: bool = True,
) -> CheapestToDeliverResult:
    """Rank the deliverables and return the CTD bond."""
    resolved_futures_price = _to_decimal(futures_price)
    candidates: list[DeliverableCandidate] = []
    for deliverable in basket.deliverables:
        cf = conversion_factor(
            contract,
            deliverable,
            prefer_published_override=prefer_published_conversion_factor,
        ).conversion_factor
        if cf <= Decimal(0):
            raise ValueError("CTD selection requires a positive conversion factor.")
        clean = deliverable.clean_price
        basis_value = gross_basis(resolved_futures_price, cf, clean)
        candidates.append(
            DeliverableCandidate(
                instrument_id=deliverable.instrument_id,
                clean_price=clean,
                conversion_factor=cf,
                futures_equivalent_price=clean / cf,
                delivery_payoff=delivery_payoff(resolved_futures_price, cf, clean),
                gross_basis=basis_value,
            )
        )
    ordered = tuple(sorted(candidates, key=lambda item: (item.gross_basis, item.instrument_id.as_str())))
    best = ordered[0]
    return CheapestToDeliverResult(
        futures_price=resolved_futures_price,
        cheapest_to_deliver=best.instrument_id,
        conversion_factor=best.conversion_factor,
        gross_basis=best.gross_basis,
        delivery_payoff=best.delivery_payoff,
        candidates=ordered,
    )


__all__ = ["CheapestToDeliverResult", "DeliverableCandidate", "cheapest_to_deliver", "delivery_payoff"]
