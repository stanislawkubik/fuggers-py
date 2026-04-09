"""Butterfly construction from fitted bond-curve residuals.

The body weight is chosen to neutralize DV01 across the short-wing and long-
wing weights implied by maturity spacing.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.pricers.bonds.risk import RiskMetrics
from fuggers_py.reference.bonds.types import CompoundingKind
from fuggers_py.core.types import Compounding, Yield
from fuggers_py.market.curves.fitted_bonds import BondCurve


def _yield_from_decimal(bond, yield_value: Decimal) -> Yield:
    method = bond.rules().compounding
    if method.kind is CompoundingKind.CONTINUOUS:
        compounding = Compounding.CONTINUOUS
    elif method.kind in {CompoundingKind.SIMPLE, CompoundingKind.DISCOUNT}:
        compounding = Compounding.SIMPLE
    elif method.frequency == 1:
        compounding = Compounding.ANNUAL
    elif method.frequency == 2:
        compounding = Compounding.SEMI_ANNUAL
    elif method.frequency == 4:
        compounding = Compounding.QUARTERLY
    else:
        compounding = Compounding.ANNUAL
    return Yield.new(yield_value, compounding)


@dataclass(frozen=True, slots=True)
class ButterflyTrade:
    """DV01-neutral butterfly trade summary."""

    short_wing_instrument_id: object
    body_instrument_id: object
    long_wing_instrument_id: object
    short_wing_weight: Decimal
    body_weight: Decimal
    long_wing_weight: Decimal
    signal_bps: Decimal


def construct_butterfly(
    fit_result: BondCurve,
    *,
    short_wing_instrument_id: object | None = None,
    body_instrument_id: object | None = None,
    long_wing_instrument_id: object | None = None,
) -> ButterflyTrade:
    """Construct a DV01-neutral butterfly trade from fitted bonds."""
    ordered = sorted(
        fit_result.bonds,
        key=lambda point: (Decimal(str(point["maturity_years"])), point["instrument_id"].as_str()),
    )
    if len(ordered) < 3:
        raise ValueError("construct_butterfly requires at least three fitted bonds.")
    short = fit_result.get_bond(short_wing_instrument_id or ordered[0]["instrument_id"])
    body = fit_result.get_bond(body_instrument_id or ordered[len(ordered) // 2]["instrument_id"])
    long = fit_result.get_bond(long_wing_instrument_id or ordered[-1]["instrument_id"])
    short_maturity = Decimal(str(short["maturity_years"]))
    body_maturity = Decimal(str(body["maturity_years"]))
    long_maturity = Decimal(str(long["maturity_years"]))
    if not (short_maturity < body_maturity < long_maturity):
        raise ValueError("construct_butterfly requires ordered maturities short < body < long.")

    span = long_maturity - short_maturity
    long_weight = (body_maturity - short_maturity) / span
    short_weight = Decimal(1) - long_weight

    short_dv01 = RiskMetrics.from_bond(
        short["bond"],
        _yield_from_decimal(short["bond"], Decimal(str(short["fitted_yield"]))),
        fit_result.date(),
    ).dv01
    body_dv01 = RiskMetrics.from_bond(
        body["bond"],
        _yield_from_decimal(body["bond"], Decimal(str(body["fitted_yield"]))),
        fit_result.date(),
    ).dv01
    long_dv01 = RiskMetrics.from_bond(
        long["bond"],
        _yield_from_decimal(long["bond"], Decimal(str(long["fitted_yield"]))),
        fit_result.date(),
    ).dv01
    if body_dv01 == Decimal(0):
        raise ValueError("construct_butterfly requires a non-zero body DV01.")
    body_weight = -((short_weight * short_dv01) + (long_weight * long_dv01)) / body_dv01
    signal_bps = (
        short_weight * Decimal(str(short["bp_residual"]))
        + body_weight * Decimal(str(body["bp_residual"]))
        + long_weight * Decimal(str(long["bp_residual"]))
    )
    return ButterflyTrade(
        short_wing_instrument_id=short["instrument_id"],
        body_instrument_id=body["instrument_id"],
        long_wing_instrument_id=long["instrument_id"],
        short_wing_weight=short_weight,
        body_weight=body_weight,
        long_wing_weight=long_weight,
        signal_bps=signal_bps,
    )


__all__ = ["ButterflyTrade", "construct_butterfly"]
