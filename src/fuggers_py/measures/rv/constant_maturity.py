"""Constant-maturity benchmark generation from fitted bond curves."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.core.types import Currency, Frequency
from fuggers_py.market.curves.fitted_bonds import (
    FittedParYieldCurve,
    FittedBondCurve,
    NotionalBenchmark,
    ParCurveSpec,
    build_notional_benchmark,
)


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class ConstantMaturityBenchmark:
    """Synthetic constant-maturity benchmark built from a fitted curve."""

    target_maturity_years: Decimal
    coupon_rate: Decimal
    fair_value_clean_price: Decimal
    fair_value_dirty_price: Decimal
    fair_value_yield: Decimal
    benchmark: NotionalBenchmark


def generate_constant_maturity_benchmark(
    fit_result: FittedBondCurve,
    target_maturity_years: object,
    *,
    component_count: int = 2,
    coupon_rate: object | None = None,
    frequency: Frequency = Frequency.SEMI_ANNUAL,
    currency: Currency = Currency.USD,
    benchmark_only: bool = True,
) -> ConstantMaturityBenchmark:
    """Generate a direct constant-maturity fair value and an auxiliary basket.

    The canonical fair value comes from the fitted curve through a synthetic
    par bond. The returned nearby-bond benchmark basket remains available as a
    separate audit utility and is not the pricing engine for the fair value.
    """

    target = _to_decimal(target_maturity_years)
    par_curve = FittedParYieldCurve.from_fit_result(
        fit_result,
        ParCurveSpec(
            frequency=frequency,
            currency=currency,
        ),
    )
    if coupon_rate is None:
        resolved_coupon = par_curve.par_yield(target)
    else:
        resolved_coupon = _to_decimal(coupon_rate)

    fair_value_clean_price = par_curve.clean_price(target, resolved_coupon)
    fair_value_dirty_price = par_curve.dirty_price(target, resolved_coupon)
    fair_value_yield = par_curve.yield_to_maturity(target, resolved_coupon)
    benchmark = build_notional_benchmark(
        fit_result,
        target,
        component_count=component_count,
        benchmark_only=benchmark_only,
    )
    return ConstantMaturityBenchmark(
        target_maturity_years=target,
        coupon_rate=resolved_coupon,
        fair_value_clean_price=fair_value_clean_price,
        fair_value_dirty_price=fair_value_dirty_price,
        fair_value_yield=fair_value_yield,
        benchmark=benchmark,
    )


__all__ = ["ConstantMaturityBenchmark", "generate_constant_maturity_benchmark"]
