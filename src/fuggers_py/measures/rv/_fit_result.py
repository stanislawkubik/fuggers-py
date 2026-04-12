"""Shared access helpers for legacy fitted-bond result rows."""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from fuggers_py.core.types import Compounding, Date, Yield
from fuggers_py.pricers.bonds.risk import RiskMetrics
from fuggers_py.reference.bonds.types import CompoundingKind

from ._shared import to_decimal


def point_metadata(point: Mapping[str, object]) -> tuple[bool | None, Decimal | None]:
    """Return benchmark and liquidity flags from one fitted-bond row."""

    reference_data = point.get("reference_data")
    if reference_data is None:
        return (None, None)
    liquidity_score = reference_data.liquidity_score
    return (reference_data.benchmark_flag, None if liquidity_score is None else to_decimal(liquidity_score))


def point_instrument_id(point: Mapping[str, object]):
    """Return the point instrument id."""

    return point["instrument_id"]


def point_maturity_years(point: Mapping[str, object]) -> Decimal:
    """Return the point maturity in years."""

    return to_decimal(point["maturity_years"])


def point_bp_residual(point: Mapping[str, object]) -> Decimal:
    """Return the basis-point residual for one fitted-bond row."""

    return to_decimal(point["bp_residual"])


def point_price_residual(point: Mapping[str, object]) -> Decimal:
    """Return the price residual for one fitted-bond row."""

    return to_decimal(point["price_residual"])


def point_fitted_yield(point: Mapping[str, object]) -> Decimal:
    """Return the fitted yield for one fitted-bond row."""

    return to_decimal(point["fitted_yield"])


def yield_from_decimal(bond, yield_value: object) -> Yield:
    """Build the bond yield object implied by a raw decimal yield."""

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
    return Yield.new(to_decimal(yield_value), compounding)


def point_dv01(point: Mapping[str, object], *, settlement_date: Date) -> Decimal:
    """Return the per-100 DV01 for one fitted-bond row."""

    return RiskMetrics.from_bond(
        point["bond"],
        yield_from_decimal(point["bond"], point_fitted_yield(point)),
        settlement_date,
    ).dv01


__all__ = [
    "point_bp_residual",
    "point_dv01",
    "point_fitted_yield",
    "point_instrument_id",
    "point_maturity_years",
    "point_metadata",
    "point_price_residual",
    "yield_from_decimal",
]
