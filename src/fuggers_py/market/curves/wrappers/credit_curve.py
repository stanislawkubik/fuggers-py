"""Credit-curve wrapper helpers.

These adapters expose survival probabilities, hazard rates, and credit spreads
from a wrapped term structure.  Curve values are raw decimals and recovery is a
fraction in ``[0, 1)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.core.types import Date

from ..conversion import ValueConverter
from ..errors import InvalidCurveInput, UnsupportedValueType
from ..term_structure import TermStructure
from ..value_type import ValueTypeKind


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class CreditCurve:
    """Adapt a term structure to credit-curve semantics.

    The wrapper interprets the underlying curve as survival probabilities,
    hazard rates, or credit spreads.  When the source curve stores credit
    spreads, the hazard rate is approximated as ``spread / (1 - recovery)``.

    Parameters
    ----------
    curve
        Wrapped term structure.
    recovery_rate
        Fractional recovery rate used for spread/hazard conversion.

    Attributes
    ----------
    curve
        Wrapped term structure used for all tenor lookups.
    recovery_rate
        Fractional recovery applied when converting between spreads and hazard
        rates.
    """

    curve: TermStructure
    recovery_rate: Decimal = Decimal("0.4")

    def __post_init__(self) -> None:
        if self.recovery_rate < Decimal(0) or self.recovery_rate >= Decimal(1):
            raise InvalidCurveInput("recovery_rate must lie in [0, 1).")

    def reference_date(self) -> Date:
        """Return the wrapped curve reference date."""

        return self.curve.reference_date()

    def max_date(self) -> Date:
        """Return the latest date supported by the wrapped curve."""

        return self.curve.max_date()

    def value_type(self) -> ValueTypeKind:
        """Return the semantic kind stored by the wrapped curve."""

        return self.curve.value_type().kind

    def _date_to_tenor(self, date: Date) -> float:
        """Convert a calendar date to a tenor using the wrapped curve."""

        return self.curve.date_to_tenor(date)

    def survival_probability_at_tenor(self, tenor: float) -> Decimal:
        """Return the survival probability at tenor ``tenor`` in years.

        The return value is derived directly from the stored curve semantics,
        with spreads converted through the configured recovery rate.
        """

        tau = float(tenor)
        if tau <= 0.0:
            return Decimal(1)

        value = float(self.curve.value_at(tau))
        match self.curve.value_type().kind:
            case ValueTypeKind.SURVIVAL_PROBABILITY:
                if value < 0.0 or value > 1.0:
                    raise InvalidCurveInput("Survival-probability curves must return values in [0, 1].")
                return _to_decimal(value)
            case ValueTypeKind.HAZARD_RATE:
                if value < 0.0:
                    raise InvalidCurveInput("Hazard-rate curves must not return negative hazards.")
                return _to_decimal(ValueConverter.hazard_to_survival(value, tau))
            case ValueTypeKind.CREDIT_SPREAD:
                loss_given_default = max(1.0 - float(self.recovery_rate), 1e-12)
                if value < 0.0:
                    raise InvalidCurveInput("Credit-spread curves must not return negative spreads.")
                hazard = value / loss_given_default
                return _to_decimal(ValueConverter.hazard_to_survival(hazard, tau))
            case _:
                raise UnsupportedValueType(
                    f"Cannot produce survival probabilities from {self.curve.value_type().kind.value}."
                )

    def hazard_rate_at_tenor(self, tenor: float) -> Decimal:
        """Return the flat hazard rate implied at tenor ``tenor`` in years.

        The wrapper converts survival probabilities or credit spreads back to a
        flat hazard rate at the requested tenor.
        """

        tau = float(tenor)
        if tau <= 0.0:
            return Decimal(0)

        value = float(self.curve.value_at(tau))
        match self.curve.value_type().kind:
            case ValueTypeKind.HAZARD_RATE:
                if value < 0.0:
                    raise InvalidCurveInput("Hazard-rate curves must not return negative hazards.")
                return _to_decimal(value)
            case ValueTypeKind.SURVIVAL_PROBABILITY:
                return _to_decimal(ValueConverter.implied_hazard_rate(value, tau))
            case ValueTypeKind.CREDIT_SPREAD:
                loss_given_default = max(1.0 - float(self.recovery_rate), 1e-12)
                if value < 0.0:
                    raise InvalidCurveInput("Credit-spread curves must not return negative spreads.")
                return _to_decimal(value / loss_given_default)
            case _:
                raise UnsupportedValueType(f"Cannot produce hazard rates from {self.curve.value_type().kind.value}.")

    def credit_spread_at_tenor(self, tenor: float) -> Decimal:
        """Return the credit spread implied at tenor ``tenor`` in years."""

        hazard = self.hazard_rate_at_tenor(tenor)
        return hazard * (Decimal(1) - self.recovery_rate)

    def survival_probability(self, date: Date) -> Decimal:
        """Return the survival probability for a calendar date."""

        return self.survival_probability_at_tenor(self._date_to_tenor(date))

    def hazard_rate(self, date: Date) -> Decimal:
        """Return the hazard rate for a calendar date."""

        return self.hazard_rate_at_tenor(self._date_to_tenor(date))

    def credit_spread(self, date: Date) -> Decimal:
        """Return the credit spread for a calendar date."""

        return self.credit_spread_at_tenor(self._date_to_tenor(date))


__all__ = ["CreditCurve"]
