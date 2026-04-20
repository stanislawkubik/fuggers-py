from __future__ import annotations

from collections.abc import Sequence

from fuggers_py._core import Currency, CurveId, Date
from fuggers_py._market.snapshot import CurvePoint
from fuggers_py.curves import CurveSpec, CurveType, ExtrapolationPolicy, YieldCurve
from fuggers_py.curves.kernels import LinearZeroKernel, LogLinearDiscountKernel


def _curve_name(curve_id: CurveId | str) -> str:
    return CurveId.parse(curve_id).as_str()


def linear_zero_curve(
    curve_id: CurveId | str,
    reference_date: Date,
    points: Sequence[CurvePoint],
    *,
    currency: Currency = Currency.USD,
    curve_type: CurveType = CurveType.NOMINAL,
    day_count: str = "ACT/365F",
    reference: str | None = None,
) -> YieldCurve:
    ordered_points = sorted(points, key=lambda point: point.tenor)
    spec = CurveSpec(
        name=_curve_name(curve_id),
        reference_date=reference_date,
        day_count=day_count,
        currency=currency,
        type=curve_type,
        reference=reference,
        extrapolation_policy=ExtrapolationPolicy.ERROR,
    )
    kernel = LinearZeroKernel(
        tenors=[float(point.tenor) for point in ordered_points],
        zero_rates=[float(point.value) for point in ordered_points],
    )
    return YieldCurve(spec=spec, kernel=kernel)


def log_linear_discount_curve(
    curve_id: CurveId | str,
    reference_date: Date,
    points: Sequence[CurvePoint],
    *,
    currency: Currency = Currency.USD,
    curve_type: CurveType = CurveType.OVERNIGHT_DISCOUNT,
    day_count: str = "ACT/365F",
    reference: str | None = None,
) -> YieldCurve:
    ordered_points = sorted(points, key=lambda point: point.tenor)
    spec = CurveSpec(
        name=_curve_name(curve_id),
        reference_date=reference_date,
        day_count=day_count,
        currency=currency,
        type=curve_type,
        reference=reference,
        extrapolation_policy=ExtrapolationPolicy.ERROR,
    )
    kernel = LogLinearDiscountKernel(
        tenors=[float(point.tenor) for point in ordered_points],
        discount_factors=[float(point.value) for point in ordered_points],
    )
    return YieldCurve(spec=spec, kernel=kernel)
