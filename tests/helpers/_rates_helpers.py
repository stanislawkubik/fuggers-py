from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal

from fuggers_py.reference.bonds.types import Tenor
from fuggers_py.core import Compounding, Currency, Date, Yield
from fuggers_py.calc import AnalyticsCurves
from fuggers_py.market.curves import CurveSpec, CurveType, DiscountingCurve, ExtrapolationPolicy, RateSpace
from fuggers_py.market.curves.multicurve import RateIndex


class FlatYieldCurve(DiscountingCurve):
    def __init__(self, reference_date: Date, rate: Decimal) -> None:
        spec = CurveSpec(
            name="tests.flat",
            reference_date=reference_date,
            day_count="ACT/365F",
            currency=Currency.USD,
            type=CurveType.NOMINAL,
            reference=None,
            extrapolation_policy=ExtrapolationPolicy.HOLD_LAST_ZERO_RATE,
        )
        super().__init__(spec)
        self._rate = rate
        self._max_t = 100.0

    @property
    def rate_space(self) -> RateSpace:
        return RateSpace.ZERO

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
class _TestMultiCurveEnvironment:
    discount_curves: dict[Currency, object] = field(default_factory=dict)
    projection_curves: dict[RateIndex, object] = field(default_factory=dict)

    def discount_curve(self, currency: Currency) -> object | None:
        return self.discount_curves.get(currency)

    def projection_curve(self, rate_index: RateIndex) -> object | None:
        return self.projection_curves.get(rate_index)


class _TestMultiCurveEnvironmentBuilder:
    def __init__(
        self,
        *,
        discount_curves: dict[Currency, object] | None = None,
        projection_curves: dict[RateIndex, object] | None = None,
    ) -> None:
        self._discount_curves = dict(discount_curves or {})
        self._projection_curves = dict(projection_curves or {})

    def add_discount_curve(self, currency: Currency, curve: object) -> "_TestMultiCurveEnvironmentBuilder":
        updated = dict(self._discount_curves)
        updated[currency] = curve
        return _TestMultiCurveEnvironmentBuilder(
            discount_curves=updated,
            projection_curves=self._projection_curves,
        )

    def add_projection_curve(self, rate_index: RateIndex, curve: object) -> "_TestMultiCurveEnvironmentBuilder":
        updated = dict(self._projection_curves)
        updated[rate_index] = curve
        return _TestMultiCurveEnvironmentBuilder(
            discount_curves=self._discount_curves,
            projection_curves=updated,
        )

    def build(self) -> _TestMultiCurveEnvironment:
        return _TestMultiCurveEnvironment(
            discount_curves=dict(self._discount_curves),
            projection_curves=dict(self._projection_curves),
        )


def flat_curve(reference_date: Date, rate: str | Decimal) -> FlatYieldCurve:
    return FlatYieldCurve(reference_date, Decimal(str(rate)))


def rate_index(name: str, tenor: str, currency: Currency = Currency.USD) -> RateIndex:
    return RateIndex.new(name, Tenor.parse(tenor), currency)


def multicurve_analytics_curves(
    *,
    discount_curve: object,
    discount_currency: Currency,
    forward_curve: object | None = None,
    projection_curves: dict[RateIndex, object] | None = None,
) -> AnalyticsCurves:
    builder = _TestMultiCurveEnvironmentBuilder().add_discount_curve(discount_currency, discount_curve)
    for index, curve in (projection_curves or {}).items():
        builder = builder.add_projection_curve(index, curve)
    return AnalyticsCurves(
        discount_curve=discount_curve,
        forward_curve=forward_curve,
        multicurve_environment=builder.build(),
        projection_curves={str(index): curve for index, curve in (projection_curves or {}).items()},
    )
