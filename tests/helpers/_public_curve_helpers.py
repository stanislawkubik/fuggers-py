from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from fuggers_py._core import Currency, CurveId, Date
from fuggers_py._runtime.snapshot import CurvePoint
from fuggers_py.curves import CurveSpec, YieldCurve
from fuggers_py.curves.kernels.nodes import LinearZeroKernel, LogLinearDiscountKernel


def _curve_name(curve_id: CurveId | str) -> str:
    return CurveId.parse(curve_id).as_str()


def linear_zero_curve(
    curve_id: CurveId | str,
    reference_date: Date,
    points: Sequence[CurvePoint],
    *,
    currency: Currency = Currency.USD,
    curve_type: str = "nominal",
    day_count: str = "ACT/365F",
    reference: str | None = None,
    extrapolation_policy: str = "error",
) -> YieldCurve:
    ordered_points = sorted(points, key=lambda point: point.tenor)
    spec = CurveSpec(
        name=_curve_name(curve_id),
        reference_date=reference_date,
        day_count=day_count,
        currency=currency,
        type=curve_type,
        reference=reference,
        extrapolation_policy=extrapolation_policy,
    )
    kernel = LinearZeroKernel(
        tenors=[float(point.tenor) for point in ordered_points],
        zero_rates=[float(point.value) for point in ordered_points],
    )
    return YieldCurve(spec=spec, kernel=kernel)


@dataclass(frozen=True, slots=True)
class DateForwardCurve:
    curve: YieldCurve

    @property
    def spec(self):
        return self.curve.spec

    @property
    def reference_date(self) -> Date:
        return self.curve.reference_date

    def max_t(self) -> float:
        return self.curve.max_t()

    def rate_at(self, tenor: float) -> float:
        return self.curve.rate_at(tenor)

    def zero_rate_at(self, tenor: float) -> float:
        return self.curve.zero_rate_at(tenor)

    def forward_rate_between(self, start_tenor: float, end_tenor: float) -> float:
        return self.curve.forward_rate_between(start_tenor, end_tenor)

    def discount_factor_at(self, tenor: float) -> float:
        return self.curve.discount_factor_at(tenor)

    def discount_factor(self, date: Date) -> Decimal:
        tau = Decimal(self.reference_date.days_between(date)) / Decimal(365)
        if tau <= 0:
            return Decimal(1)
        return Decimal(str(self.curve.discount_factor_at(float(tau))))

    def forward_rate(self, start: Date, end: Date) -> Decimal:
        day_count = start.days_between(end)
        if day_count == 0:
            raise ValueError("forward_rate requires distinct start and end dates.")
        df_start = self.discount_factor(start)
        df_end = self.discount_factor(end)
        if df_end == 0:
            raise ValueError("forward_rate requires a non-zero discount factor at end date.")
        return (df_start / df_end - Decimal(1)) / (Decimal(day_count) / Decimal(365))


def date_forward_curve(curve: YieldCurve) -> DateForwardCurve:
    return DateForwardCurve(curve)


def log_linear_discount_curve(
    curve_id: CurveId | str,
    reference_date: Date,
    points: Sequence[CurvePoint],
    *,
    currency: Currency = Currency.USD,
    curve_type: str = "overnight_discount",
    day_count: str = "ACT/365F",
    reference: str | None = None,
    extend_last_discount_factor_to: Decimal | None = None,
) -> YieldCurve:
    ordered_points = sorted(points, key=lambda point: point.tenor)
    if extend_last_discount_factor_to is not None:
        tail_tenor = Decimal(str(extend_last_discount_factor_to))
        if tail_tenor > ordered_points[-1].tenor:
            ordered_points.append(CurvePoint(tail_tenor, ordered_points[-1].value))
    spec = CurveSpec(
        name=_curve_name(curve_id),
        reference_date=reference_date,
        day_count=day_count,
        currency=currency,
        type=curve_type,
        reference=reference,
        extrapolation_policy="error",
    )
    kernel = LogLinearDiscountKernel(
        tenors=[float(point.tenor) for point in ordered_points],
        discount_factors=[float(point.value) for point in ordered_points],
    )
    return YieldCurve(spec=spec, kernel=kernel)
