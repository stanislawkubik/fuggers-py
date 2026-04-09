"""Inflation-index projection curves."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Date
from fuggers_py.reference.inflation.conventions import InflationConvention

from .._semantics import stored_value_type
from ..discrete import DiscreteCurve


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class InflationIndexCurve:
    """Projected inflation index levels anchored to an observed reference CPI.

    The internal state is a ratio curve relative to ``reference_date``. Daily
    projected CPI levels are obtained as:

    ``projected_reference_cpi(date) = anchor_reference_cpi * projected_index_ratio(date, reference_date)``
    """

    reference_date: Date
    anchor_reference_cpi: Decimal
    convention: InflationConvention
    curve: DiscreteCurve

    def __post_init__(self) -> None:
        object.__setattr__(self, "anchor_reference_cpi", _to_decimal(self.anchor_reference_cpi))
        if self.anchor_reference_cpi <= Decimal(0):
            raise ValueError("InflationIndexCurve requires a positive anchor_reference_cpi.")
        if self.curve.date() != self.reference_date:
            raise ValueError("InflationIndexCurve curve.date() must match reference_date.")
        if stored_value_type(self.curve).kind.value != "INFLATION_INDEX_RATIO":
            raise ValueError("InflationIndexCurve requires a curve with ValueType.INFLATION_INDEX_RATIO.")

    def projected_reference_cpi(self, date: Date) -> Decimal:
        """Return the projected daily reference CPI for ``date``."""

        return self.anchor_reference_cpi * self._ratio_at(date)

    def projected_index_ratio(self, date: Date, base_date: Date | None = None) -> Decimal:
        """Return the projected index ratio between ``base_date`` and ``date``."""

        if base_date is None:
            return self._ratio_at(date)
        base_cpi = self.projected_reference_cpi(base_date)
        if base_cpi == Decimal(0):
            raise ValueError("InflationIndexCurve base_date implies a zero projected CPI.")
        return self.projected_reference_cpi(date) / base_cpi

    def zero_inflation_rate(
        self,
        start: Date,
        end: Date,
        *,
        day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED,
    ) -> Decimal:
        """Return the annualized zero inflation rate between ``start`` and ``end``."""

        if end <= start:
            raise ValueError("InflationIndexCurve.zero_inflation_rate requires end after start.")
        ratio = self.projected_index_ratio(end, start)
        if ratio <= Decimal(0):
            raise ValueError("InflationIndexCurve.zero_inflation_rate requires a positive index ratio.")
        year_fraction = day_count.to_day_count().year_fraction(start, end)
        if year_fraction <= Decimal(0):
            raise ValueError("InflationIndexCurve.zero_inflation_rate requires a positive year fraction.")
        annualized = math.exp(math.log(float(ratio)) / float(year_fraction)) - 1.0
        return Decimal(str(annualized))

    def reference_cpi(self, date: Date, convention: InflationConvention | None = None) -> Decimal:
        """Compatibility adapter for existing inflation pricers."""

        self._validate_convention(convention)
        return self.projected_reference_cpi(date)

    def get_reference_cpi(self, date: Date, convention: InflationConvention | None = None) -> Decimal:
        """Alias kept for compatibility with existing projection adapters."""

        return self.reference_cpi(date, convention)

    def _ratio_at(self, date: Date) -> Decimal:
        value = self.curve.value_at_date(date)
        return Decimal(str(value))

    def _validate_convention(self, convention: InflationConvention | None) -> None:
        if convention is None:
            return
        if convention.index_source != self.convention.index_source or convention.currency != self.convention.currency:
            raise ValueError(
                "InflationIndexCurve convention mismatch: "
                f"expected {self.convention.currency.code()} {self.convention.index_source}, "
                f"got {convention.currency.code()} {convention.index_source}."
            )


InflationCurve = InflationIndexCurve


__all__ = ["InflationCurve", "InflationIndexCurve"]
