"""Bond-layer yield helpers shared by bonds and analytics.

Unsuffixed current-yield helpers return raw decimal rates. Use the explicit
``*_pct`` wrappers for quoted percentage display values.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import exp

from fuggers_py.math import SolverConfig, brent, newton_raphson
from fuggers_py.math.errors import ConvergenceFailed, DivisionByZero, InvalidBracket
from fuggers_py.reference.bonds.errors import BondPricingError, YieldConvergenceFailed
from fuggers_py.reference.bonds.types import YieldConvention


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def current_yield(coupon_rate: object, clean_price: object) -> Decimal:
    """Return current yield as a raw decimal from a coupon rate and clean price.

    Parameters
    ----------
    coupon_rate
        Annual coupon rate as a decimal, for example ``0.05`` for 5%.
    clean_price
        Clean price quoted in percent-of-par, for example ``99.25``.

    Returns
    -------
    Decimal
        Current yield as a raw decimal, for example ``0.05`` for 5%.
    """

    price = _to_decimal(clean_price)
    if price <= 0:
        raise BondPricingError(reason="Clean price must be positive for current yield.")
    rate = _to_decimal(coupon_rate)
    annual_coupon = rate * Decimal(100)
    return annual_coupon / price


def current_yield_from_amount(coupon_amount: object, clean_price: object) -> Decimal:
    """Return current yield as a raw decimal from annual coupon cash amount."""

    price = _to_decimal(clean_price)
    if price <= 0:
        raise BondPricingError(reason="Clean price must be positive for current yield.")
    amount = _to_decimal(coupon_amount)
    return amount / price


def current_yield_from_bond(bond: object, clean_price: object) -> Decimal:
    """Return current yield as a raw decimal using coupon per 100 face.

    The bond's actual notional is ignored on purpose so the result uses the
    same per-100-face convention as the clean price input.
    """

    if hasattr(bond, "coupon_rate"):
        rate = bond.coupon_rate() if callable(bond.coupon_rate) else bond.coupon_rate
    else:
        raise BondPricingError(reason="Bond does not expose coupon_rate for current yield.")

    coupon_amount = _to_decimal(rate) * Decimal(100)
    return current_yield_from_amount(coupon_amount, clean_price)


def current_yield_simple(coupon_rate: float, clean_price: float) -> float:
    """Float-based variant of :func:`current_yield` returning a raw decimal."""

    if clean_price <= 0:
        raise BondPricingError(reason="Clean price must be positive for current yield.")
    return float(coupon_rate) * 100.0 / float(clean_price)


def current_yield_pct(coupon_rate: object, clean_price: object) -> Decimal:
    """Return current yield in quoted percentage points."""

    return current_yield(coupon_rate, clean_price) * Decimal(100)


def current_yield_from_amount_pct(coupon_amount: object, clean_price: object) -> Decimal:
    """Return current yield in quoted percentage points."""

    return current_yield_from_amount(coupon_amount, clean_price) * Decimal(100)


def current_yield_from_bond_pct(bond: object, clean_price: object) -> Decimal:
    """Return current yield from a bond-like object in quoted percentage points."""

    return current_yield_from_bond(bond, clean_price) * Decimal(100)


def current_yield_simple_pct(coupon_rate: float, clean_price: float) -> float:
    """Float-based current-yield helper returning quoted percentage points."""

    return current_yield_simple(coupon_rate, clean_price) * 100.0


@dataclass(frozen=True, slots=True)
class YieldResult:
    """Result container for solved bond yields.

    Attributes
    ----------
    yield_value
        Solved yield as a raw decimal, for example ``0.045`` for 4.5%.
    iterations
        Number of solver iterations consumed.
    residual
        Pricing residual at the reported solution.
    method
        Name of the numerical method that produced the result.
    convention
        Yield compounding convention used during discounting.
    converged
        Whether the underlying numerical routine reported convergence.
    """

    yield_value: float
    iterations: int
    residual: float
    method: str
    convention: YieldConvention
    converged: bool = True

    def yield_percent(self) -> float:
        """Return the solved yield as a percentage."""

        return float(self.yield_value) * 100.0

    def yield_decimal(self) -> float:
        """Return the solved yield as a raw decimal."""

        return float(self.yield_value)


@dataclass(frozen=True, slots=True)
class YieldSolver:
    """Numerically solve bond yield from dirty price and cashflows."""

    tolerance: float = 1e-10
    max_iterations: int = 100

    def _discount_factor(self, y: float, t: float, *, convention: YieldConvention, frequency: int) -> float:
        tt = float(t)
        if tt == 0.0:
            return 1.0
        if convention in {
            YieldConvention.STREET_CONVENTION,
            YieldConvention.TRUE_YIELD,
            YieldConvention.BOND_EQUIVALENT_YIELD,
            YieldConvention.ANNUAL,
        }:
            f = float(max(1, frequency))
            return float((1.0 + y / f) ** (-tt * f))
        if convention is YieldConvention.CONTINUOUS:
            return exp(-y * tt)
        if convention in {YieldConvention.SIMPLE_YIELD, YieldConvention.DISCOUNT_YIELD}:
            return 1.0 / (1.0 + y * tt)
        f = float(max(1, frequency))
        return float((1.0 + y / f) ** (-tt * f))

    def _discount_factor_derivative(self, y: float, t: float, *, convention: YieldConvention, frequency: int) -> float:
        tt = float(t)
        if tt == 0.0:
            return 0.0
        df = self._discount_factor(y, tt, convention=convention, frequency=frequency)
        if convention in {
            YieldConvention.STREET_CONVENTION,
            YieldConvention.TRUE_YIELD,
            YieldConvention.BOND_EQUIVALENT_YIELD,
            YieldConvention.ANNUAL,
        }:
            f = float(max(1, frequency))
            return -tt * df / (1.0 + y / f)
        if convention is YieldConvention.CONTINUOUS:
            return -tt * df
        if convention in {YieldConvention.SIMPLE_YIELD, YieldConvention.DISCOUNT_YIELD}:
            return -tt / ((1.0 + y * tt) ** 2)
        f = float(max(1, frequency))
        return -tt * df / (1.0 + y / f)

    def solve(
        self,
        *,
        dirty_price: float,
        cashflows: list[float],
        times: list[float],
        frequency: int,
        convention: YieldConvention = YieldConvention.STREET_CONVENTION,
        initial_guess: float | None = None,
    ) -> YieldResult:
        """Solve the yield that reproduces the supplied dirty price.

        Parameters
        ----------
        dirty_price
            Dirty price in percent-of-par.
        cashflows
            Future coupon and redemption cash amounts.
        times
            Year fractions from settlement to each cashflow.
        frequency
            Coupon or compounding frequency used by periodic conventions.
        convention
            Yield convention that defines the discount-factor formula.
        initial_guess
            Optional starting guess as a raw decimal yield.
        """

        if len(cashflows) != len(times):
            raise BondPricingError(reason="cashflows and times length mismatch.")
        if not cashflows:
            raise BondPricingError(reason="No cashflows supplied to yield solver.")

        target = float(dirty_price)

        def pv_at_yield(y: float) -> float:
            return sum(
                cf * self._discount_factor(y, t, convention=convention, frequency=frequency)
                for cf, t in zip(cashflows, times, strict=True)
            )

        def pv_derivative(y: float) -> float:
            return sum(
                cf * self._discount_factor_derivative(y, t, convention=convention, frequency=frequency)
                for cf, t in zip(cashflows, times, strict=True)
            )

        guess = (
            float(initial_guess)
            if initial_guess is not None
            else self._estimate_initial_yield(cashflows, times, target)
        )

        def objective(y: float) -> float:
            return pv_at_yield(y) - target

        config = SolverConfig(tolerance=self.tolerance, max_iterations=self.max_iterations)

        def _try_newton(g: float) -> YieldResult | None:
            try:
                res = newton_raphson(objective, pv_derivative, g, config=config)
            except (ConvergenceFailed, DivisionByZero):
                return None
            return YieldResult(
                yield_value=float(res.root),
                iterations=int(res.iterations),
                residual=float(res.residual),
                method="Newton",
                convention=convention,
                converged=bool(res.converged),
            )

        result = _try_newton(guess)
        if result is not None:
            return result

        for g in (0.01, 0.03, 0.05, 0.08, 0.10, 0.15):
            result = _try_newton(float(g))
            if result is not None:
                return result

        for a, b in [
            (guess - 0.1, guess + 0.1),
            (-0.1, 0.5),
            (-0.2, 1.0),
            (-0.5, 2.0),
        ]:
            try:
                res = brent(objective, float(a), float(b), config=config)
            except (InvalidBracket, ConvergenceFailed):
                continue
            return YieldResult(
                yield_value=float(res.root),
                iterations=int(res.iterations),
                residual=float(res.residual),
                method="Brent",
                convention=convention,
                converged=bool(res.converged),
            )

        raise YieldConvergenceFailed(iterations=self.max_iterations, residual=abs(float(objective(guess))))

    @staticmethod
    def _estimate_initial_yield(cashflows: list[float], times: list[float], dirty_price: float) -> float:
        """Estimate a starting yield guess from the cashflow profile.

        The heuristic uses the maturity horizon and last cashflow as a crude
        approximation of the coupon level, then scales that against the dirty
        price to seed the numerical root finder.
        """

        if not cashflows:
            return 0.05
        years_to_maturity = max(times[-1], 1e-12)
        face_value = min(cashflows[-1], 100.0)
        total_amount = sum(cashflows)
        annual_coupon = (total_amount - face_value) / years_to_maturity
        if dirty_price > 0.0:
            guess = annual_coupon / dirty_price
            return max(min(guess, 1.0), -0.5)
        return 0.05


__all__ = [
    "YieldResult",
    "YieldSolver",
    "current_yield",
    "current_yield_pct",
    "current_yield_from_amount",
    "current_yield_from_amount_pct",
    "current_yield_from_bond",
    "current_yield_from_bond_pct",
    "current_yield_simple",
    "current_yield_simple_pct",
]
