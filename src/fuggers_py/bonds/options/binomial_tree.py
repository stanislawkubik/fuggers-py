"""Recombining binomial tree utilities for callable bond pricing."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable

from fuggers_py.bonds.traits import BondCashFlow
from fuggers_py._core.types import Date

from .models import ShortRateModel


ExerciseRule = Callable[[Date, float, float], float]
# Callback that chooses between immediate exercise value and continuation.


@dataclass(frozen=True, slots=True)
class BinomialTree:
    """Recombining binomial tree over a sorted set of event dates.

    The tree propagates bond cash flows or option payoffs through a
    recombining short-rate lattice on the supplied event dates.
    """

    model: ShortRateModel
    dates: tuple[Date, ...]

    @classmethod
    def new(cls, model: ShortRateModel, dates: list[Date]) -> "BinomialTree":
        """Create a tree from a model and a set of event dates."""
        ordered = tuple(sorted(set(dates)))
        if len(ordered) < 2:
            raise ValueError("BinomialTree requires at least two dates.")
        return cls(model=model, dates=ordered)

    def value_lattice(
        self,
        cashflows: list[BondCashFlow],
        *,
        spread: Decimal = Decimal(0),
        coupon_map: dict[Date, Decimal] | None = None,
        principal_map: dict[Date, Decimal] | None = None,
    ) -> list[list[float]]:
        """Return the bond value lattice discounted with an additive spread.

        ``spread`` is a raw decimal spread added to the short rate in the
        discount factor. The optional maps override the cash-flow allocation by
        date when the caller needs custom coupon/principal splits.
        """
        spread_value = float(spread)
        coupon_amounts = {cf.date: Decimal(0) for cf in cashflows}
        principal_amounts = {cf.date: Decimal(0) for cf in cashflows}
        if coupon_map is not None:
            coupon_amounts.update(coupon_map)
        if principal_map is not None:
            principal_amounts.update(principal_map)
        for cf in cashflows:
            if coupon_map is None:
                if cf.is_principal():
                    principal_amounts[cf.date] = principal_amounts.get(cf.date, Decimal(0)) + cf.factored_amount()
                else:
                    coupon_amounts[cf.date] = coupon_amounts.get(cf.date, Decimal(0)) + cf.factored_amount()

        intervals = len(self.dates) - 1
        layers: list[list[float]] = [[0.0 for _ in range(intervals + 1)]]
        values = [0.0] * (intervals + 1)
        for step in range(intervals - 1, -1, -1):
            start = self.dates[step]
            end = self.dates[step + 1]
            dt = max(float(start.days_between(end)) / 365.0, 1e-12)
            coupon = float(coupon_amounts.get(end, Decimal(0)))
            principal = float(principal_amounts.get(end, Decimal(0)))
            next_values = values
            new_values: list[float] = []
            for level in range(step + 1):
                continuation = 0.5 * (next_values[level] + next_values[level + 1])
                short_rate = self.model.node_rate(start, end, level=level, width=step)
                discounted = continuation * self.model.discount(short_rate, dt, spread=spread_value)
                new_values.append(coupon + principal + discounted)
            values = new_values
            layers.insert(0, new_values)
        return layers

    def price_cashflows(
        self,
        cashflows: list[BondCashFlow],
        *,
        spread: Decimal = Decimal(0),
        exercise: ExerciseRule | None = None,
        coupon_map: dict[Date, Decimal] | None = None,
        principal_map: dict[Date, Decimal] | None = None,
    ) -> Decimal:
        """Price cash flows across the tree, optionally applying exercise logic."""
        spread_value = float(spread)
        coupon_amounts = {cf.date: Decimal(0) for cf in cashflows}
        principal_amounts = {cf.date: Decimal(0) for cf in cashflows}
        if coupon_map is not None:
            coupon_amounts.update(coupon_map)
        if principal_map is not None:
            principal_amounts.update(principal_map)
        for cf in cashflows:
            if coupon_map is None:
                if cf.is_principal():
                    principal_amounts[cf.date] = principal_amounts.get(cf.date, Decimal(0)) + cf.factored_amount()
                else:
                    coupon_amounts[cf.date] = coupon_amounts.get(cf.date, Decimal(0)) + cf.factored_amount()

        intervals = len(self.dates) - 1
        values = [0.0] * (intervals + 1)
        for step in range(intervals - 1, -1, -1):
            start = self.dates[step]
            end = self.dates[step + 1]
            dt = max(float(start.days_between(end)) / 365.0, 1e-12)
            coupon = float(coupon_amounts.get(end, Decimal(0)))
            principal = float(principal_amounts.get(end, Decimal(0)))
            next_values = values
            new_values: list[float] = []
            for level in range(step + 1):
                continuation = 0.5 * (next_values[level] + next_values[level + 1])
                short_rate = self.model.node_rate(start, end, level=level, width=step)
                discounted = continuation * self.model.discount(short_rate, dt, spread=spread_value)
                if exercise is not None:
                    node_value = exercise(end, coupon + principal, discounted)
                else:
                    node_value = coupon + principal + discounted
                new_values.append(node_value)
            values = new_values
        return Decimal(str(values[0]))

__all__ = ["BinomialTree", "ExerciseRule"]
