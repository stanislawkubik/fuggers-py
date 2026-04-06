"""Bond yield engine.

This module discounts future cash flows to obtain dirty prices and inverts the
same cash flows to solve for yield. Prices are interpreted against the
settlement date using the bond's configured day-count and compounding rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.reference.bonds.errors import InvalidBondSpec, YieldConvergenceFailed
from fuggers_py.products.bonds.traits import BondCashFlow
from fuggers_py.reference.bonds.types import YieldCalculationRules
from fuggers_py.reference.bonds.types.yield_convention import YieldConvention
from fuggers_py.core.daycounts import ActActIcma
from fuggers_py.core.types import Date
from fuggers_py.math import SolverConfig, brent, newton_raphson
from fuggers_py.math.errors import ConvergenceFailed, DivisionByZero, InvalidBracket


@dataclass(frozen=True, slots=True)
class CashFlowData:
    """Single discounted cash flow used by the yield solver.

    ``years`` is the settlement-relative year fraction and ``amount`` is the
    factored cash-flow amount in percent-of-par terms.
    """

    years: float
    amount: float


@dataclass(frozen=True, slots=True)
class YieldEngineResult:
    """Result of a yield-solver iteration.

    The solver reports the converged yield, iteration count, residual, and the
    convention used to interpret the yield.
    """

    yield_rate: float
    iterations: int
    converged: bool
    residual: float
    method: str
    convention: YieldConvention


def _to_float(x: Decimal | float | int) -> float:
    if isinstance(x, Decimal):
        return float(x)
    return float(x)


def _pv_at_yield(cashflows: list[CashFlowData], yield_rate: float, *, rules: YieldCalculationRules) -> float:
    compounding = rules.compounding
    y = float(yield_rate)
    pv = 0.0
    for cf in cashflows:
        pv += cf.amount * compounding.discount_factor(y, cf.years)
    return pv


def _pv_derivative(cashflows: list[CashFlowData], yield_rate: float, *, rules: YieldCalculationRules) -> float:
    compounding = rules.compounding
    y = float(yield_rate)
    dv = 0.0
    for cf in cashflows:
        dv += cf.amount * compounding.discount_factor_derivative(y, cf.years)
    return dv


def _prepare_cashflows(
    cashflows: list[BondCashFlow],
    *,
    settlement_date: Date,
    rules: YieldCalculationRules,
) -> list[CashFlowData]:
    """Filter and transform cash flows into settlement-relative solver inputs.

    Only cash flows strictly after settlement are kept. Act/Act ICMA uses the
    coupon-period boundaries from the cash-flow metadata so year fractions are
    accumulated across periods rather than measured directly from settlement to
    each payment date.
    """
    day_count = rules.accrual_day_count_obj()
    future = [cf for cf in cashflows if cf.date > settlement_date]
    future.sort(key=lambda cf: cf.date)

    if isinstance(day_count, ActActIcma) and all(
        (cf.accrual_start is not None and cf.accrual_end is not None) for cf in future
    ):
        # Act/Act ICMA requires coupon-period boundaries. We derive
        # settlement-to-payment times by accumulating over coupon periods.
        times: list[float] = []
        cumulative = 0.0
        for i, cf in enumerate(future):
            accrual_start = cf.accrual_start
            accrual_end = cf.accrual_end
            if accrual_start is None or accrual_end is None:  # pragma: no cover - defensive
                break

            if i == 0 and settlement_date > accrual_start:
                period = day_count.year_fraction_with_period(
                    settlement_date,
                    accrual_end,
                    accrual_start,
                    accrual_end,
                )
            else:
                period = day_count.year_fraction_with_period(
                    accrual_start,
                    accrual_end,
                    accrual_start,
                    accrual_end,
                )

            cumulative += float(period)
            times.append(cumulative)

        return [
            CashFlowData(years=t, amount=_to_float(cf.factored_amount()))
            for t, cf in zip(times, future, strict=True)
        ]

    return [
        CashFlowData(
            years=float(day_count.year_fraction(settlement_date, cf.date)),
            amount=_to_float(cf.factored_amount()),
        )
        for cf in future
    ]


def _estimate_initial_yield(cashflows: list[CashFlowData], *, dirty_price: float, rules: YieldCalculationRules) -> float:
    if not cashflows:
        return 0.05

    total_amount = sum(cf.amount for cf in cashflows)
    years_to_maturity = max(cashflows[-1].years, 1e-12)
    face_value = min(cashflows[-1].amount, 100.0)

    annual_coupon = (total_amount - face_value) / years_to_maturity
    if dirty_price > 0.0:
        guess = annual_coupon / dirty_price
        return max(min(guess, 1.0), -0.5)
    return 0.05


def _solve_with_brent(
    objective,
    initial_guess: float,
    *,
    config: SolverConfig,
    convention: YieldConvention,
) -> YieldEngineResult | None:
    brackets: list[tuple[float, float]] = [
        (initial_guess - 0.1, initial_guess + 0.1),
        (-0.1, 0.5),
        (-0.2, 1.0),
        (-0.5, 2.0),
    ]

    for a, b in brackets:
        try:
            res = brent(objective, a, b, config=config)
        except (InvalidBracket, ConvergenceFailed):
            continue
        return YieldEngineResult(
            yield_rate=float(res.root),
            iterations=int(res.iterations),
            converged=bool(res.converged),
            residual=float(res.residual),
            method="Brent",
            convention=convention,
        )
    return None


@dataclass(frozen=True, slots=True)
class StandardYieldEngine:
    """Standard dirty-price/yield solver for bond cash flows.

    The engine prices future cash flows to a dirty price and inverts that
    relationship to solve for yield under the bond's configured day-count and
    compounding rules.
    """

    tolerance: float = 1e-10
    max_iterations: int = 100

    def yield_from_price(
        self,
        cashflows: list[BondCashFlow],
        *,
        clean_price: Decimal,
        accrued: Decimal,
        settlement_date: Date,
        rules: YieldCalculationRules,
    ) -> YieldEngineResult:
        """Solve the raw decimal yield that matches a clean price plus accrued.

        ``clean_price`` and ``accrued`` are summed to obtain the dirty price
        used by the solver. The returned yield is a raw decimal quote in the
        bond's configured convention.
        """
        dirty_price = _to_float(clean_price + accrued)
        target = float(dirty_price)
        cf_data = _prepare_cashflows(cashflows, settlement_date=settlement_date, rules=rules)
        if not cf_data:
            raise InvalidBondSpec(reason="No future cashflows found for yield calculation.")

        initial_guess = _estimate_initial_yield(cf_data, dirty_price=dirty_price, rules=rules)

        objective = lambda y: _pv_at_yield(cf_data, y, rules=rules) - target
        derivative = lambda y: _pv_derivative(cf_data, y, rules=rules)

        config = SolverConfig(tolerance=self.tolerance, max_iterations=self.max_iterations)

        def _try_newton(guess: float) -> YieldEngineResult | None:
            try:
                res = newton_raphson(objective, derivative, guess, config=config)
            except (ConvergenceFailed, DivisionByZero):
                return None
            return YieldEngineResult(
                yield_rate=float(res.root),
                iterations=int(res.iterations),
                converged=bool(res.converged),
                residual=float(res.residual),
                method="Newton",
                convention=rules.convention,
            )

        result = _try_newton(initial_guess)
        if result is not None:
            return self._apply_rounding(result, rules=rules)

        for guess in (0.01, 0.03, 0.05, 0.08, 0.10, 0.15):
            result = _try_newton(float(guess))
            if result is not None:
                return self._apply_rounding(result, rules=rules)

        brent_result = _solve_with_brent(objective, initial_guess, config=config, convention=rules.convention)
        if brent_result is not None:
            return self._apply_rounding(brent_result, rules=rules)

        residual = abs(float(objective(initial_guess)))
        raise YieldConvergenceFailed(iterations=self.max_iterations, residual=residual)

    def dirty_price_from_yield(
        self,
        cashflows: list[BondCashFlow],
        *,
        yield_rate: float,
        settlement_date: Date,
        rules: YieldCalculationRules,
    ) -> float:
        """Return the dirty price implied by a raw decimal yield.

        The result is a percent-of-par dirty price on the supplied settlement
        date.
        """
        cf_data = _prepare_cashflows(cashflows, settlement_date=settlement_date, rules=rules)
        return _pv_at_yield(cf_data, float(yield_rate), rules=rules)

    @staticmethod
    def _apply_rounding(result: YieldEngineResult, *, rules: YieldCalculationRules) -> YieldEngineResult:
        if rules.rounding is None:
            return result
        rounded = float(rules.rounding.apply(result.yield_rate))
        return YieldEngineResult(
            yield_rate=rounded,
            iterations=result.iterations,
            converged=result.converged,
            residual=result.residual,
            method=result.method,
            convention=result.convention,
        )


__all__ = [
    "CashFlowData",
    "YieldEngineResult",
    "StandardYieldEngine",
]
