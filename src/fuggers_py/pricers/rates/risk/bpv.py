"""Finite-difference DV01/PV01/BPV helpers for rates products.

The default bump is one basis point. Returned values use the shared signed
convention: positive when PV rises as rates fall by 1 bp.
"""

from __future__ import annotations

from decimal import Decimal

from fuggers_py.market.state import AnalyticsCurves
from fuggers_py.products.rates import BasisSwap, FixedFloatSwap, Fra, Ois

from .._curve_resolver import analytics_curves_with_parallel_bump
from ..basis_swap_pricer import BasisSwapPricer
from ..fra_pricer import FraPricer
from ..swap_pricer import SwapPricer


def _relevant_currency_and_indices(instrument) -> tuple[object, tuple[object, ...]]:
    if isinstance(instrument, (FixedFloatSwap, Ois)):
        return instrument.currency(), (instrument.floating_leg.rate_index(),)
    if isinstance(instrument, Fra):
        rate_index = instrument.rate_index()
        return instrument.currency, () if rate_index is None else (rate_index,)
    if isinstance(instrument, BasisSwap):
        return instrument.currency(), (instrument.pay_leg.rate_index(), instrument.receive_leg.rate_index())
    raise TypeError(f"Unsupported rates instrument type: {type(instrument).__name__}.")


def _pv(instrument, curves: AnalyticsCurves, pricer: object | None = None) -> Decimal:
    if isinstance(instrument, (FixedFloatSwap, Ois)):
        return (pricer if isinstance(pricer, SwapPricer) else SwapPricer()).pv(instrument, curves)
    if isinstance(instrument, Fra):
        return (pricer if isinstance(pricer, FraPricer) else FraPricer()).pv(instrument, curves)
    if isinstance(instrument, BasisSwap):
        return (pricer if isinstance(pricer, BasisSwapPricer) else BasisSwapPricer()).pv(instrument, curves)
    raise TypeError(f"Unsupported rates instrument type: {type(instrument).__name__}.")


def pv01(
    instrument,
    curves: AnalyticsCurves,
    *,
    bump: object = Decimal("0.0001"),
    pricer: object | None = None,
) -> Decimal:
    """Return the parallel PV01 for a rates instrument.

    Parameters
    ----------
    instrument:
        Supported rates instrument to analyze.
    curves:
        Analytics curves used for valuation.
    bump:
        Parallel curve shift in raw decimal form. The default is one basis
        point.
    pricer:
        Optional pricer instance matching the instrument type.

    Returns
    -------
    Decimal
        Finite-difference PV sensitivity in currency units per one basis point
        of parallel curve shift, signed positive when rates fall and PV rises.
    """

    bump_decimal = Decimal(str(bump))
    currency, indices = _relevant_currency_and_indices(instrument)
    bumped_up = analytics_curves_with_parallel_bump(
        curves,
        currency=currency,
        projection_indices=indices,
        bump=bump_decimal,
    )
    bumped_down = analytics_curves_with_parallel_bump(
        curves,
        currency=currency,
        projection_indices=indices,
        bump=-bump_decimal,
    )
    scale = bump_decimal / Decimal("0.0001")
    if scale == Decimal(0):
        raise ValueError("pv01 requires a non-zero bump size.")
    return (_pv(instrument, bumped_down, pricer) - _pv(instrument, bumped_up, pricer)) / (Decimal(2) * scale)


def swap_pv01(
    instrument: FixedFloatSwap | Ois,
    curves: AnalyticsCurves,
    *,
    bump: object = Decimal("0.0001"),
    pricer: SwapPricer | None = None,
) -> Decimal:
    """Return the PV01 for a fixed-float or overnight-indexed swap."""

    return pv01(instrument, curves, bump=bump, pricer=pricer or SwapPricer())


def fra_pv01(
    instrument: Fra,
    curves: AnalyticsCurves,
    *,
    bump: object = Decimal("0.0001"),
    pricer: FraPricer | None = None,
) -> Decimal:
    """Return the PV01 for an FRA."""

    return pv01(instrument, curves, bump=bump, pricer=pricer or FraPricer())


def basis_swap_pv01(
    instrument: BasisSwap,
    curves: AnalyticsCurves,
    *,
    bump: object = Decimal("0.0001"),
    pricer: BasisSwapPricer | None = None,
) -> Decimal:
    """Return the PV01 for a same-currency basis swap."""

    return pv01(instrument, curves, bump=bump, pricer=pricer or BasisSwapPricer())


bpv = pv01
dv01 = pv01
swap_dv01 = swap_pv01
fra_dv01 = fra_pv01
basis_swap_dv01 = basis_swap_pv01


__all__ = [
    "basis_swap_dv01",
    "basis_swap_pv01",
    "bpv",
    "dv01",
    "fra_dv01",
    "fra_pv01",
    "pv01",
    "swap_dv01",
    "swap_pv01",
]
