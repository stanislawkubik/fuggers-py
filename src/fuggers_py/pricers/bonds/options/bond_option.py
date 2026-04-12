"""Bond option pricing built on the short-rate tree utilities."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from fuggers_py.market.curve_support import curve_reference_date
from fuggers_py.products.bonds.traits import Bond
from fuggers_py.core.types import Date

from .binomial_tree import BinomialTree
from .errors import ModelError
from .models import ShortRateModel


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class OptionType(str, Enum):
    """Directional option type on the underlying bond value."""

    CALL = "CALL"
    PUT = "PUT"


class ExerciseStyle(str, Enum):
    """Exercise timing supported by the tree pricer."""

    EUROPEAN = "EUROPEAN"
    AMERICAN = "AMERICAN"


@dataclass(frozen=True, slots=True)
class BondOption:
    """Option on a bond valued by a short-rate recombining tree.

    The option is priced off the bond's cash flows and a supplied short-rate
    model. The returned value is in the same pricing units as the bond
    cash-flow lattice, not a quoted yield.
    """

    expiry: Date
    strike: Decimal
    bond: Bond | None = None
    model: ShortRateModel | None = None
    option_type: OptionType = OptionType.CALL
    exercise_style: ExerciseStyle = ExerciseStyle.EUROPEAN
    valuation_date: Date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "strike", _to_decimal(self.strike))
        if self.strike <= 0:
            raise ModelError(reason="Bond option strike must be positive.")

    def price(
        self,
        *,
        bond: Bond | None = None,
        model: ShortRateModel | None = None,
        valuation_date: Date | None = None,
    ) -> Decimal:
        """Price the option with the configured or supplied bond and model.

        The result is the option value in the same pricing units as the bond
        cash flows passed through the tree. American exercise compares the
        immediate payoff with the discounted continuation value at each node.
        """
        instrument = bond or self.bond
        short_rate_model = model or self.model
        if instrument is None:
            raise ModelError(reason="BondOption.price requires an underlying bond.")
        if short_rate_model is None:
            raise ModelError(reason="BondOption.price requires a short-rate model.")

        value_date = valuation_date or self.valuation_date or curve_reference_date(short_rate_model.term_structure)
        if value_date >= self.expiry:
            intrinsic = self._payoff(Decimal("0"))
            return intrinsic
        if self.expiry > instrument.maturity_date():
            raise ModelError(reason="Bond option expiry must be on or before bond maturity.")

        event_dates = {value_date, self.expiry}
        event_dates.update(cf.date for cf in instrument.cash_flows(value_date) if cf.date > value_date)
        tree = BinomialTree.new(short_rate_model, sorted(event_dates))
        lattice = tree.value_lattice(instrument.cash_flows(value_date))
        expiry_step = tree.dates.index(self.expiry)
        option_values = [float(self._payoff(Decimal(str(value)))) for value in lattice[expiry_step]]

        for step in range(expiry_step - 1, -1, -1):
            start = tree.dates[step]
            end = tree.dates[step + 1]
            dt = max(float(start.days_between(end)) / 365.0, 1e-12)
            next_values = option_values
            new_values: list[float] = []
            for level in range(step + 1):
                continuation = 0.5 * (next_values[level] + next_values[level + 1])
                short_rate = short_rate_model.node_rate(start, end, level=level, width=step)
                discounted = continuation * short_rate_model.discount(short_rate, dt)
                if self.exercise_style is ExerciseStyle.AMERICAN:
                    immediate = float(self._payoff(Decimal(str(lattice[step][level]))))
                    new_values.append(max(immediate, discounted))
                else:
                    new_values.append(discounted)
            option_values = new_values
        return Decimal(str(option_values[0]))

    def _payoff(self, underlying_value: Decimal) -> Decimal:
        if self.option_type is OptionType.CALL:
            return max(underlying_value - self.strike, Decimal(0))
        return max(self.strike - underlying_value, Decimal(0))


__all__ = ["BondOption", "ExerciseStyle", "OptionType"]
