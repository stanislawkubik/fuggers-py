"""Effective convexity (`fuggers_py.measures.risk.convexity.effective`).

The effective path bumps yield up and down and reports convexity as a
positive-magnitude estimate.
"""

from __future__ import annotations

from decimal import Decimal

from fuggers_py.pricers.bonds import BondPricer as _BondPricer
from fuggers_py.products.bonds.traits import Bond
from fuggers_py.core.types import Date, Yield

from ..dv01 import _to_decimal


def effective_convexity(
    bond: Bond,
    ytm: Yield,
    settlement_date: Date,
    *,
    bump: float = 1e-4,
) -> Decimal:
    """Return convexity from symmetric yield bumps around the input yield."""

    pricer = _BondPricer()
    rules = bond.rules()
    y = float(pricer._yield_to_engine_rate(ytm, rules=rules))
    cashflows = bond.cash_flows()

    p0 = pricer.engine.dirty_price_from_yield(
        cashflows,
        yield_rate=y,
        settlement_date=settlement_date,
        rules=rules,
    )
    pp = pricer.engine.dirty_price_from_yield(
        cashflows,
        yield_rate=y + bump,
        settlement_date=settlement_date,
        rules=rules,
    )
    pm = pricer.engine.dirty_price_from_yield(
        cashflows,
        yield_rate=y - bump,
        settlement_date=settlement_date,
        rules=rules,
    )

    if p0 == 0.0:
        return Decimal(0)

    convexity = (pp + pm - 2.0 * p0) / (p0 * bump * bump)
    return _to_decimal(convexity)


__all__ = ["effective_convexity"]
