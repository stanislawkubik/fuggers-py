from __future__ import annotations

import math
from decimal import Decimal

from fuggers_py.reference.bonds.types import Tenor
from fuggers_py.core import Compounding, Currency, Date, Yield
from fuggers_py.core.traits import YieldCurve
from fuggers_py.market.curves import MultiCurveEnvironmentBuilder, RateIndex
from fuggers_py.calc import AnalyticsCurves


class FlatYieldCurve(YieldCurve):
    def __init__(self, reference_date: Date, rate: Decimal) -> None:
        self._reference_date = reference_date
        self._rate = rate

    def reference_date(self) -> Date:
        return self._reference_date

    def discount_factor(self, date: Date) -> Decimal:
        tau = Decimal(self._reference_date.days_between(date)) / Decimal(365)
        return Decimal(str(math.exp(-float(self._rate) * float(tau))))

    def zero_rate(self, date: Date) -> Yield:
        return Yield.new(self._rate, Compounding.CONTINUOUS)

    def max_date(self) -> Date:
        return self._reference_date.add_days(365 * 50)


def flat_curve(reference_date: Date, rate: str | Decimal) -> FlatYieldCurve:
    return FlatYieldCurve(reference_date, Decimal(str(rate)))


def rate_index(name: str, tenor: str, currency: Currency = Currency.USD) -> RateIndex:
    return RateIndex.new(name, Tenor.parse(tenor), currency)


def multicurve_analytics_curves(
    *,
    discount_curve: YieldCurve,
    discount_currency: Currency,
    forward_curve: YieldCurve | None = None,
    projection_curves: dict[RateIndex, YieldCurve] | None = None,
) -> AnalyticsCurves:
    builder = MultiCurveEnvironmentBuilder().add_discount_curve(discount_currency, discount_curve)
    for index, curve in (projection_curves or {}).items():
        builder = builder.add_projection_curve(index, curve)
    return AnalyticsCurves(
        discount_curve=discount_curve,
        forward_curve=forward_curve,
        multicurve_environment=builder.build(),
        projection_curves={str(index): curve for index, curve in (projection_curves or {}).items()},
    )
