"""Butterfly construction from fitted bond-curve residuals.

The body weight is chosen to neutralize DV01 across the short-wing and long-
wing weights implied by maturity spacing.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py._core.types import Compounding, Yield
from fuggers_py._curves_impl.fitted_bonds import BondCurve
from fuggers_py._pricers.bonds.risk import RiskMetrics
from fuggers_py._core.compounding import CompoundingKind


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
        key=lambda point: (
            point["maturity_years"] if isinstance(point["maturity_years"], Decimal) else Decimal(str(point["maturity_years"])),
            point["instrument_id"].as_str(),
        ),
    )
    if len(ordered) < 3:
        raise ValueError("construct_butterfly requires at least three fitted bonds.")
    short = fit_result.get_bond(short_wing_instrument_id or ordered[0]["instrument_id"])
    body = fit_result.get_bond(body_instrument_id or ordered[len(ordered) // 2]["instrument_id"])
    long = fit_result.get_bond(long_wing_instrument_id or ordered[-1]["instrument_id"])
    short_maturity = short["maturity_years"] if isinstance(short["maturity_years"], Decimal) else Decimal(str(short["maturity_years"]))
    body_maturity = body["maturity_years"] if isinstance(body["maturity_years"], Decimal) else Decimal(str(body["maturity_years"]))
    long_maturity = long["maturity_years"] if isinstance(long["maturity_years"], Decimal) else Decimal(str(long["maturity_years"]))
    if not (short_maturity < body_maturity < long_maturity):
        raise ValueError("construct_butterfly requires ordered maturities short < body < long.")

    span = long_maturity - short_maturity
    long_weight = (body_maturity - short_maturity) / span
    short_weight = Decimal(1) - long_weight

    short_yield = short["fitted_yield"] if isinstance(short["fitted_yield"], Decimal) else Decimal(str(short["fitted_yield"]))
    short_method = short["bond"].rules().compounding
    if short_method.kind is CompoundingKind.CONTINUOUS:
        short_compounding = Compounding.CONTINUOUS
    elif short_method.kind in {CompoundingKind.SIMPLE, CompoundingKind.DISCOUNT}:
        short_compounding = Compounding.SIMPLE
    elif short_method.frequency == 1:
        short_compounding = Compounding.ANNUAL
    elif short_method.frequency == 2:
        short_compounding = Compounding.SEMI_ANNUAL
    elif short_method.frequency == 4:
        short_compounding = Compounding.QUARTERLY
    else:
        short_compounding = Compounding.ANNUAL
    short_dv01 = RiskMetrics.from_bond(short["bond"], Yield.new(short_yield, short_compounding), fit_result.date()).dv01
    body_yield = body["fitted_yield"] if isinstance(body["fitted_yield"], Decimal) else Decimal(str(body["fitted_yield"]))
    body_method = body["bond"].rules().compounding
    if body_method.kind is CompoundingKind.CONTINUOUS:
        body_compounding = Compounding.CONTINUOUS
    elif body_method.kind in {CompoundingKind.SIMPLE, CompoundingKind.DISCOUNT}:
        body_compounding = Compounding.SIMPLE
    elif body_method.frequency == 1:
        body_compounding = Compounding.ANNUAL
    elif body_method.frequency == 2:
        body_compounding = Compounding.SEMI_ANNUAL
    elif body_method.frequency == 4:
        body_compounding = Compounding.QUARTERLY
    else:
        body_compounding = Compounding.ANNUAL
    body_dv01 = RiskMetrics.from_bond(body["bond"], Yield.new(body_yield, body_compounding), fit_result.date()).dv01
    long_yield = long["fitted_yield"] if isinstance(long["fitted_yield"], Decimal) else Decimal(str(long["fitted_yield"]))
    long_method = long["bond"].rules().compounding
    if long_method.kind is CompoundingKind.CONTINUOUS:
        long_compounding = Compounding.CONTINUOUS
    elif long_method.kind in {CompoundingKind.SIMPLE, CompoundingKind.DISCOUNT}:
        long_compounding = Compounding.SIMPLE
    elif long_method.frequency == 1:
        long_compounding = Compounding.ANNUAL
    elif long_method.frequency == 2:
        long_compounding = Compounding.SEMI_ANNUAL
    elif long_method.frequency == 4:
        long_compounding = Compounding.QUARTERLY
    else:
        long_compounding = Compounding.ANNUAL
    long_dv01 = RiskMetrics.from_bond(long["bond"], Yield.new(long_yield, long_compounding), fit_result.date()).dv01
    if body_dv01 == Decimal(0):
        raise ValueError("construct_butterfly requires a non-zero body DV01.")
    body_weight = -((short_weight * short_dv01) + (long_weight * long_dv01)) / body_dv01
    signal_bps = (
        short_weight
        * (short["bp_residual"] if isinstance(short["bp_residual"], Decimal) else Decimal(str(short["bp_residual"])))
        + body_weight
        * (body["bp_residual"] if isinstance(body["bp_residual"], Decimal) else Decimal(str(body["bp_residual"])))
        + long_weight
        * (long["bp_residual"] if isinstance(long["bp_residual"], Decimal) else Decimal(str(long["bp_residual"])))
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
