"""Spread duration helpers (`fuggers_py.measures.risk.duration.spread_duration`).

When a curve is supplied, spread duration uses a curve-bump path that shifts
the zero curve in parallel. Without a curve, it falls back to a yield-bump
effective-duration approximation. Both paths return positive-magnitude
duration values.
"""

from __future__ import annotations

from decimal import Decimal

from fuggers_py.products.bonds.traits import Bond
from fuggers_py.core.types import Date, Yield
from fuggers_py.market.curve_support import parallel_bumped_curve
from fuggers_py.market.curves import DiscountingCurve

from ...pricing import BondPricer
from .effective import effective_duration
from ...errors import AnalyticsError


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _spread_duration_from_curve(
    bond: Bond,
    curve: DiscountingCurve,
    settlement_date: Date,
    *,
    spread: object | None = None,
    bump: float = 1e-4,
) -> Decimal:
    """Return spread duration from a parallel bump to the supplied curve."""

    sprd = float(_to_decimal(spread or 0))
    pricer = BondPricer()

    base_curve = parallel_bumped_curve(curve, sprd)
    p0 = pricer.price_from_curve(bond, base_curve, settlement_date).dirty.as_percentage()
    if p0 == 0:
        return Decimal(0)

    curve_up = parallel_bumped_curve(curve, sprd + bump)
    curve_dn = parallel_bumped_curve(curve, sprd - bump)

    p_up = pricer.price_from_curve(bond, curve_up, settlement_date).dirty.as_percentage()
    p_dn = pricer.price_from_curve(bond, curve_dn, settlement_date).dirty.as_percentage()

    duration = (p_dn - p_up) / (Decimal(2) * p0 * Decimal(str(bump)))
    return duration


def spread_duration(
    bond: Bond,
    ytm: Yield | None,
    settlement_date: Date,
    *,
    bump: float = 1e-4,
    curve: DiscountingCurve | None = None,
    spread: object | None = None,
) -> Decimal:
    """Return spread duration using curve-bump or yield-bump logic.

    Parameters
    ----------
    bond : Bond
        Bond whose spread duration is being measured.
    ytm : Yield or None
        Yield used by the fallback path when no curve is supplied.
    settlement_date : Date
        Settlement date for pricing.
    bump : float, optional
        Symmetric bump size used in the finite-difference approximation.
    curve : TermStructure or None, optional
        If supplied, the curve-bump path is used.
    spread : object or None, optional
        Parallel spread shift applied before the bump when ``curve`` is given.
    """

    if curve is not None:
        return _spread_duration_from_curve(
            bond,
            curve,
            settlement_date,
            spread=spread,
            bump=bump,
        )

    if ytm is None:
        raise AnalyticsError.invalid_input("spread_duration requires ytm when curve is not supplied.")

    return effective_duration(bond, ytm, settlement_date, bump=bump)


__all__ = ["spread_duration"]
