"""Term-structure interface for curve primitives.

The curve layer measures tenors as year fractions from a curve date and
evaluates raw decimal values at those tenors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Compounding, Date, Yield

from .conversion import ValueConverter
from .errors import UnsupportedValueType
from .value_type import ValueType, ValueTypeKind


class TermStructure(ABC):
    """Abstract base class for tenor-based curve objects.

    Implementations expose a curve date and a tenor-based value function.
    """

    @abstractmethod
    def date(self) -> Date:
        """Return the anchor date from which tenors are measured."""

    @abstractmethod
    def value_at_tenor(self, tenor_years: float) -> float:
        """Return the raw curve value at tenor ``t`` in years."""

    def derivative_at_tenor(self, tenor_years: float) -> float | None:  # noqa: D401 - part of trait
        """Return the tenor derivative of :meth:`value_at`, if available."""

        return None

    def value_type(self) -> ValueType | None:
        """Return the semantic value type carried by the curve, if any."""

        value = getattr(self, "_value_type", None)
        return value if isinstance(value, ValueType) else None

    def value_at_date(self, date: Date) -> float:
        """Return the raw curve value for a calendar date."""

        return self.value_at_tenor(self.date_to_tenor(date))

    def date_to_tenor(self, date: Date, *, day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED) -> float:
        """Convert ``date`` to a year-fraction tenor from the reference date."""

        yf = day_count.to_day_count().year_fraction(self.date(), date)
        return float(yf)

    def tenor_to_date(self, t: float) -> Date:
        """Convert tenor ``t`` in years to an approximate calendar date."""

        days = int(round(float(t) * 365.0))
        return self.date().add_days(days)

    def discount_factor_at_tenor(self, tenor_years: float) -> float:
        """Return the discount factor implied at tenor ``tenor_years``."""

        tenor = float(tenor_years)
        if tenor <= 0.0:
            return 1.0

        value_type = self.value_type()
        if value_type is None:
            raise UnsupportedValueType(f"{type(self).__name__} does not define discounting semantics.")

        match value_type.kind:
            case ValueTypeKind.DISCOUNT_FACTOR | ValueTypeKind.SURVIVAL_PROBABILITY:
                return float(self.value_at_tenor(tenor))
            case ValueTypeKind.ZERO_RATE:
                rate = float(self.value_at_tenor(tenor))
                compounding = value_type.compounding or Compounding.CONTINUOUS
                return ValueConverter.zero_to_df(rate, tenor, compounding)
            case ValueTypeKind.HAZARD_RATE:
                hazard = float(self.value_at_tenor(tenor))
                return ValueConverter.hazard_to_survival(hazard, tenor)
            case _:
                raise UnsupportedValueType(
                    f"Cannot produce a discount factor from {value_type.kind.value}."
                )

    def zero_rate_at_tenor(
        self,
        tenor_years: float,
        *,
        compounding: Compounding = Compounding.CONTINUOUS,
    ) -> float:
        """Return the zero rate implied at tenor ``tenor_years``."""

        tenor = float(tenor_years)
        if tenor <= 0.0:
            return 0.0

        value_type = self.value_type()
        if value_type is None:
            raise UnsupportedValueType(f"{type(self).__name__} does not define zero-rate semantics.")

        match value_type.kind:
            case ValueTypeKind.DISCOUNT_FACTOR | ValueTypeKind.SURVIVAL_PROBABILITY:
                return ValueConverter.df_to_zero(float(self.value_at_tenor(tenor)), tenor, compounding)
            case ValueTypeKind.ZERO_RATE:
                rate = float(self.value_at_tenor(tenor))
                stored_compounding = value_type.compounding or Compounding.CONTINUOUS
                return ValueConverter.convert_compounding(rate, stored_compounding, compounding)
            case ValueTypeKind.HAZARD_RATE:
                survival = ValueConverter.hazard_to_survival(float(self.value_at_tenor(tenor)), tenor)
                return ValueConverter.df_to_zero(survival, tenor, compounding)
            case _:
                raise UnsupportedValueType(
                    f"Cannot produce a zero rate from {value_type.kind.value}."
                )

    def forward_rate_at_tenors(
        self,
        start_tenor_years: float,
        end_tenor_years: float,
        *,
        compounding: Compounding = Compounding.CONTINUOUS,
    ) -> float:
        """Return the forward rate implied between two tenors."""

        start_tenor = float(start_tenor_years)
        end_tenor = float(end_tenor_years)
        if end_tenor <= start_tenor:
            raise ValueError("forward_rate_at_tenors requires end_tenor_years > start_tenor_years.")

        return ValueConverter.forward_rate_from_dfs(
            self.discount_factor_at_tenor(start_tenor),
            self.discount_factor_at_tenor(end_tenor),
            start_tenor,
            end_tenor,
            compounding,
        )

    def discount_factor(self, date: Date) -> Decimal:
        """Return the discount factor from ``date()`` to ``date``."""

        return Decimal(str(self.discount_factor_at_tenor(self.date_to_tenor(date))))

    def zero_rate(self, date: Date) -> Yield:
        """Return the continuously compounded zero rate from ``date()`` to ``date``."""

        return Yield.new(
            Decimal(
                str(
                    self.zero_rate_at_tenor(
                        self.date_to_tenor(date),
                        compounding=Compounding.CONTINUOUS,
                    )
                )
            ),
            Compounding.CONTINUOUS,
        )

    def forward_rate(self, start: Date, end: Date) -> Decimal:
        """Return the annualized simple forward rate between ``start`` and ``end``."""

        start_tenor = self.date_to_tenor(start)
        end_tenor = self.date_to_tenor(end)
        return Decimal(
            str(
                self.forward_rate_at_tenors(
                    start_tenor,
                    end_tenor,
                    compounding=Compounding.SIMPLE,
                )
            )
        )
