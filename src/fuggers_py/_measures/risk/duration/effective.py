"""Effective duration (`fuggers_py._measures.risk.duration.effective`).

The effective-duration path bumps the yield up and down symmetrically and
returns the positive-magnitude duration estimate.
"""

from __future__ import annotations

from decimal import Decimal

from fuggers_py._pricers.bonds import BondPricer as _BondPricer
from fuggers_py._products.bonds.traits import Bond
from fuggers_py._core.types import Date, Yield

from ..dv01 import _to_decimal


def effective_duration(
    bond: Bond,
    ytm: Yield,
    settlement_date: Date,
    *,
    bump: float = 1e-4,
) -> Decimal:
    """Return effective duration from symmetric yield bumps."""

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

    duration = (pm - pp) / (2.0 * p0 * bump)
    return _to_decimal(duration)


__all__ = ["effective_duration"]
