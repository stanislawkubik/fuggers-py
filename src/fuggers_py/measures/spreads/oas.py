"""Option-adjusted spread helpers.

OAS values are solved as raw decimal spreads. Sensitivity helpers report
spread duration and convexity around a 1 bp bump, and ``option_value`` is the
bullet price minus the callable price.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.products.bonds.instruments import CallableBond
from fuggers_py.pricers.bonds.options import BinomialTree, HullWhiteModel
from fuggers_py.core.types import Date
from fuggers_py.market.curve_support import parallel_bumped_curve
from fuggers_py.math import SolverConfig, brent, newton_raphson
from fuggers_py.math.errors import ConvergenceFailed, DivisionByZero, InvalidBracket

from ..errors import AnalyticsError


DEFAULT_SOLVER_CONFIG = SolverConfig(tolerance=1e-10, max_iterations=200)


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class OASCalculator:
    """Hull-White callable-bond OAS solver and sensitivity helper."""

    model: HullWhiteModel
    solver_config: SolverConfig = DEFAULT_SOLVER_CONFIG

    def calculate(self, callable_bond: CallableBond, market_price: object, settlement: Date) -> Decimal:
        """Solve the callable bond OAS as a raw decimal spread."""
        if settlement >= callable_bond.maturity_date():
            raise AnalyticsError.invalid_settlement("Settlement date is on or after maturity.")
        target = float(_to_decimal(market_price))

        def objective(oas: float) -> float:
            return float(self.price_with_oas(callable_bond, Decimal(str(oas)), settlement)) - target

        def derivative(oas: float) -> float:
            bump = 1e-5
            up = float(self.price_with_oas(callable_bond, Decimal(str(oas + bump)), settlement))
            down = float(self.price_with_oas(callable_bond, Decimal(str(oas - bump)), settlement))
            return (up - down) / (2.0 * bump)

        try:
            result = newton_raphson(objective, derivative, 0.0, config=self.solver_config)
            return Decimal(str(result.root))
        except (ConvergenceFailed, DivisionByZero):
            pass

        for lower, upper in [(-0.05, 0.1), (-0.1, 0.2), (-0.25, 0.5)]:
            try:
                result = brent(objective, lower, upper, config=self.solver_config)
                return Decimal(str(result.root))
            except (ConvergenceFailed, InvalidBracket):
                continue

        raise AnalyticsError.spread_failed("OAS solver failed to converge.")

    def price_with_oas(self, callable_bond: CallableBond, oas_decimal: object, settlement: Date) -> Decimal:
        """Price the callable bond using a raw-decimal OAS."""
        if settlement >= callable_bond.maturity_date():
            raise AnalyticsError.invalid_settlement("Settlement date is on or after maturity.")
        oas = _to_decimal(oas_decimal)
        tree = BinomialTree.new(self.model, self._event_dates(callable_bond, settlement))
        coupon_map, principal_map = self._cash_maps(callable_bond, settlement)
        call_map = {
            entry.call_date: callable_bond.call_price_on(entry.call_date)
            for entry in callable_bond.call_schedule.future_entries(settlement)
            if callable_bond.call_price_on(entry.call_date) is not None
        }

        def exercise(date: Date, scheduled_cash: float, discounted_continuation: float) -> float:
            call_price = call_map.get(date)
            if call_price is None or date >= callable_bond.maturity_date():
                return scheduled_cash + discounted_continuation
            coupon = float(coupon_map.get(date, Decimal(0)))
            principal = float(principal_map.get(date, Decimal(0)))
            return coupon + min(principal + discounted_continuation, float(call_price))

        return tree.price_cashflows(
            callable_bond.cash_flows(settlement),
            spread=oas,
            exercise=exercise,
            coupon_map=coupon_map,
            principal_map=principal_map,
        )

    def effective_duration(self, callable_bond: CallableBond, oas_decimal: object, settlement: Date, *, bump: float = 1e-4) -> Decimal:
        """Return effective duration around a 1 bp curve bump."""
        oas = _to_decimal(oas_decimal)
        p0 = float(self.price_with_oas(callable_bond, oas, settlement))
        p_up = float(self._with_bumped_curve(bump).price_with_oas(callable_bond, oas, settlement))
        p_down = float(self._with_bumped_curve(-bump).price_with_oas(callable_bond, oas, settlement))
        if p0 == 0.0:
            return Decimal(0)
        return Decimal(str((p_down - p_up) / (2.0 * p0 * bump)))

    def effective_convexity(self, callable_bond: CallableBond, oas_decimal: object, settlement: Date, *, bump: float = 1e-4) -> Decimal:
        """Return effective convexity around a 1 bp curve bump."""
        oas = _to_decimal(oas_decimal)
        p0 = float(self.price_with_oas(callable_bond, oas, settlement))
        p_up = float(self._with_bumped_curve(bump).price_with_oas(callable_bond, oas, settlement))
        p_down = float(self._with_bumped_curve(-bump).price_with_oas(callable_bond, oas, settlement))
        if p0 == 0.0:
            return Decimal(0)
        return Decimal(str((p_up + p_down - 2.0 * p0) / (p0 * bump * bump)))

    def option_value(self, callable_bond: CallableBond, oas_decimal: object, settlement: Date) -> Decimal:
        """Return the embedded-option value as bullet price minus callable price."""
        tree = BinomialTree.new(self.model, self._event_dates(callable_bond, settlement))
        coupon_map, principal_map = self._cash_maps(callable_bond, settlement)
        bullet = tree.price_cashflows(
            callable_bond.cash_flows(settlement),
            spread=_to_decimal(oas_decimal),
            coupon_map=coupon_map,
            principal_map=principal_map,
        )
        callable_price = self.price_with_oas(callable_bond, oas_decimal, settlement)
        return bullet - callable_price

    def _cash_maps(self, callable_bond: CallableBond, settlement: Date) -> tuple[dict[Date, Decimal], dict[Date, Decimal]]:
        coupon_map: dict[Date, Decimal] = {}
        principal_map: dict[Date, Decimal] = {}
        for cf in callable_bond.cash_flows(settlement):
            if cf.is_principal():
                principal = callable_bond.notional() if cf.flow_type.name == "COUPON_AND_PRINCIPAL" else cf.factored_amount()
                coupon = cf.factored_amount() - principal
                coupon_map[cf.date] = coupon_map.get(cf.date, Decimal(0)) + coupon
                principal_map[cf.date] = principal_map.get(cf.date, Decimal(0)) + principal
            else:
                coupon_map[cf.date] = coupon_map.get(cf.date, Decimal(0)) + cf.factored_amount()
        return coupon_map, principal_map

    def _event_dates(self, callable_bond: CallableBond, settlement: Date) -> list[Date]:
        dates = {settlement}
        dates.update(cf.date for cf in callable_bond.cash_flows(settlement))
        dates.update(entry.call_date for entry in callable_bond.call_schedule.future_entries(settlement))
        return sorted(dates)

    def _with_bumped_curve(self, bump: float) -> "OASCalculator":
        bumped_curve = parallel_bumped_curve(self.model.term_structure, bump)
        bumped_model = HullWhiteModel(
            mean_reversion=self.model.mean_reversion,
            volatility=self.model.volatility,
            term_structure=bumped_curve,
        )
        return OASCalculator(model=bumped_model, solver_config=self.solver_config)


__all__ = ["OASCalculator"]
