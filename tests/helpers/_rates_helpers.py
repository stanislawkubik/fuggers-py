from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal

from fuggers_py._core import Compounding, Currency, Date, Tenor, Yield
from fuggers_py._runtime.state import AnalyticsCurves
from fuggers_py.curves import CurveSpec, DiscountingCurve
from fuggers_py.curves.multicurve import RateIndex


class FlatYieldCurve(DiscountingCurve):
    def __init__(self, reference_date: Date, rate: Decimal) -> None:
        spec = CurveSpec(
            name="tests.flat",
            reference_date=reference_date,
            day_count="ACT/365F",
            currency=Currency.USD,
            type="nominal",
            reference=None,
            extrapolation_policy="hold_last_zero_rate",
        )
        super().__init__(spec)
        self._rate = rate
        self._max_t = 100.0

    def max_t(self) -> float:
        return self._max_t

    def rate_at(self, tenor: float) -> float:
        self._check_t(float(tenor))
        return float(self._rate)

    def discount_factor_at(self, tenor: float) -> float:
        checked_tenor = float(tenor)
        self._check_t(checked_tenor)
        if checked_tenor <= 0.0:
            return 1.0
        return math.exp(-float(self._rate) * checked_tenor)

    def date(self) -> Date:
        return self.reference_date

    def discount_factor(self, date: Date) -> Decimal:
        tau = Decimal(self.reference_date.days_between(date)) / Decimal(365)
        if tau <= 0:
            return Decimal(1)
        return Decimal(str(math.exp(-float(self._rate) * float(tau))))

    def zero_rate(self, date: Date) -> Yield:
        return Yield.new(self._rate, Compounding.CONTINUOUS)

    def forward_rate(self, start: Date, end: Date) -> Decimal:
        day_count = start.days_between(end)
        if day_count == 0:
            raise ValueError("forward_rate requires distinct start and end dates.")
        df_start = self.discount_factor(start)
        df_end = self.discount_factor(end)
        if df_end == 0:
            raise ValueError("forward_rate requires a non-zero discount factor at end date.")
        tau = Decimal(day_count) / Decimal(365)
        return (df_start / df_end - Decimal(1)) / tau


@dataclass(frozen=True, slots=True)
class _TestCurveEnvironment:
    discount_curves: dict[Currency, object] = field(default_factory=dict)
    projection_curves: dict[RateIndex, object] = field(default_factory=dict)

    def discount_curve(self, currency: Currency) -> object | None:
        return self.discount_curves.get(currency)

    def projection_curve(self, rate_index: RateIndex) -> object | None:
        return self.projection_curves.get(rate_index)


def flat_curve(reference_date: Date, rate: str | Decimal) -> FlatYieldCurve:
    return FlatYieldCurve(reference_date, Decimal(str(rate)))


def rate_index(name: str, tenor: str, currency: Currency = Currency.USD) -> RateIndex:
    return RateIndex.new(name, Tenor.parse(tenor), currency)


def multicurve_analytics_curves(
    *,
    discount_curve: object,
    discount_currency: Currency,
    forward_curve: object | None = None,
    fx_forward_curve: object | None = None,
    projection_curves: dict[RateIndex, object] | None = None,
    additional_discount_curves: dict[Currency, object] | None = None,
) -> AnalyticsCurves:
    resolved_discount_curves = {discount_currency: discount_curve}
    resolved_discount_curves.update(additional_discount_curves or {})
    resolved_projection_curves = dict(projection_curves or {})
    return AnalyticsCurves(
        discount_curve=discount_curve,
        forward_curve=forward_curve,
        fx_forward_curve=fx_forward_curve,
        multicurve_environment=_TestCurveEnvironment(
            discount_curves=resolved_discount_curves,
            projection_curves=resolved_projection_curves,
        ),
        projection_curves={str(index): curve for index, curve in resolved_projection_curves.items()},
    )
