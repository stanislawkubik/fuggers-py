"""Z-spread helpers.

The core Z-spread solver returns a raw decimal spread. The calculator wrapper
converts that result to basis points for the public ``spread_bps`` API.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import exp

from fuggers_py.products.bonds.traits import Bond, BondCashFlow
from fuggers_py.core.types import Date, Price
from fuggers_py.market.curves.term_structure import TermStructure
from fuggers_py.math import SolverConfig, brent, newton_raphson
from fuggers_py.math.errors import ConvergenceFailed, DivisionByZero, InvalidBracket

from ..errors import AnalyticsError


def _to_float(value: object) -> float:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Price):
        return float(value.as_percentage())
    return float(value)


def _prepare_cashflows(
    cashflows: list[BondCashFlow],
    *,
    settlement_date: Date,
    curve: TermStructure,
) -> list[tuple[float, float]]:
    df_settle = float(curve.discount_factor(settlement_date))
    if df_settle == 0.0:
        raise AnalyticsError.spread_failed("Discount factor at settlement is zero.")

    future = [cf for cf in cashflows if cf.date > settlement_date]
    future.sort(key=lambda cf: cf.date)

    prepared: list[tuple[float, float]] = []
    for cf in future:
        t = float(settlement_date.days_between(cf.date)) / 365.0
        df = float(curve.discount_factor(cf.date)) / df_settle
        prepared.append((t, float(cf.factored_amount()) * df))
    return prepared


def z_spread_from_curve(
    cashflows: list[BondCashFlow],
    *,
    dirty_price: object,
    curve: TermStructure,
    settlement_date: Date,
) -> Decimal:
    """Solve the Z-spread in raw decimal form from dirty price and cash flows."""
    prepared = _prepare_cashflows(cashflows, settlement_date=settlement_date, curve=curve)
    if not prepared:
        raise AnalyticsError.spread_failed("No future cashflows for Z-spread.")

    target = _to_float(dirty_price)

    def pv_at_z(z: float) -> float:
        return sum(cf * exp(-z * t) for t, cf in prepared)

    def pv_derivative(z: float) -> float:
        return sum(-t * cf * exp(-z * t) for t, cf in prepared)

    objective = lambda z: pv_at_z(z) - target

    config = SolverConfig(tolerance=1e-10, max_iterations=200)

    def _try_newton(guess: float) -> float | None:
        try:
            res = newton_raphson(objective, pv_derivative, guess, config=config)
        except (ConvergenceFailed, DivisionByZero):
            return None
        return float(res.root)

    guess = 0.0
    z = _try_newton(guess)
    if z is not None:
        return Decimal(str(z))

    for a, b in [(-0.05, 0.2), (-0.1, 0.5), (-0.5, 2.0)]:
        try:
            res = brent(objective, a, b, config=config)
        except (InvalidBracket, ConvergenceFailed):
            continue
        return Decimal(str(res.root))

    raise AnalyticsError.spread_failed("Z-spread solver failed to converge.")


def z_spread(
    bond: Bond,
    price: Price,
    curve: TermStructure,
    settlement_date: Date,
) -> Decimal:
    """Solve the Z-spread in raw decimal form using a clean bond price.

    The supplied clean price is converted to dirty price by adding accrued
    interest before the root solve.
    """
    accrued = bond.accrued_interest(settlement_date)
    dirty_price = price.as_percentage() + accrued
    return z_spread_from_curve(
        bond.cash_flows(),
        dirty_price=dirty_price,
        curve=curve,
        settlement_date=settlement_date,
    )


@dataclass(frozen=True, slots=True)
class ZSpreadCalculator:
    """Curve-backed Z-spread calculator with basis-point output.

    Parameters
    ----------
    curve:
        Curve used to discount future bond cash flows.
    """

    curve: TermStructure

    def spread_bps(self, bond: Bond, price: Price, settlement_date: Date) -> Decimal:
        """Return the Z-spread in basis points for a clean price input."""
        spread = z_spread(bond, price, self.curve, settlement_date)
        return spread * Decimal(10_000)


__all__ = ["ZSpreadCalculator", "z_spread", "z_spread_from_curve"]
