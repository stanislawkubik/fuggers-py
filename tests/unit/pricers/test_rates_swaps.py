from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.core import Currency, Date, Frequency
from fuggers_py.calc import AnalyticsCurves
from fuggers_py.pricers.rates import SwapPricer
from fuggers_py.products.rates import (
    FixedFloatSwap,
    FixedLegSpec,
    FloatingLegSpec,
    PayReceive,
    ScheduleDefinition,
)

from tests.helpers._rates_helpers import flat_curve, multicurve_analytics_curves, rate_index


def _swap(*, effective_date: Date, maturity_date: Date, fixed_rate: str | Decimal) -> FixedFloatSwap:
    return FixedFloatSwap(
        effective_date=effective_date,
        maturity_date=maturity_date,
        fixed_leg=FixedLegSpec(
            pay_receive=PayReceive.RECEIVE,
            notional=Decimal("1000000"),
            fixed_rate=Decimal(str(fixed_rate)),
            currency=Currency.USD,
            schedule=ScheduleDefinition(frequency=Frequency.SEMI_ANNUAL),
        ),
        floating_leg=FloatingLegSpec(
            pay_receive=PayReceive.PAY,
            notional=Decimal("1000000"),
            index_name="SOFR",
            index_tenor="3M",
            currency=Currency.USD,
            schedule=ScheduleDefinition(frequency=Frequency.QUARTERLY),
        ),
    )


def test_swap_pricer_par_rate_pv_and_annuity_on_flat_curve() -> None:
    reference_date = Date.from_ymd(2026, 1, 2)
    curve = flat_curve(reference_date, "0.04")
    curves = AnalyticsCurves(discount_curve=curve, forward_curve=curve)
    pricer = SwapPricer()

    seed_swap = _swap(
        effective_date=reference_date,
        maturity_date=reference_date.add_years(2),
        fixed_rate="0.00",
    )
    par_rate = pricer.par_rate(seed_swap, curves)
    par_swap = _swap(
        effective_date=reference_date,
        maturity_date=reference_date.add_years(2),
        fixed_rate=par_rate,
    )
    result = pricer.price(par_swap, curves)
    expected_annuity = sum(
        (
            par_swap.fixed_leg.notional
            * period.year_fraction
            * curve.discount_factor(period.payment_date)
        )
        for period in par_swap.fixed_periods()
    )

    assert result.annuity == expected_annuity
    assert result.par_rate == par_rate
    assert float(result.present_value) == pytest.approx(0.0, abs=1e-10)
    assert float(result.fixed_leg_pv) == pytest.approx(-float(result.floating_leg_pv), abs=1e-10)


def test_swap_pricer_prefers_multicurve_environment_when_present() -> None:
    reference_date = Date.from_ymd(2026, 1, 2)
    discount_curve = flat_curve(reference_date, "0.03")
    fallback_forward_curve = flat_curve(reference_date, "0.03")
    projection_curve = flat_curve(reference_date, "0.04")
    sofr_3m = rate_index("SOFR", "3M")
    pricer = SwapPricer()
    swap = _swap(
        effective_date=reference_date,
        maturity_date=reference_date.add_years(3),
        fixed_rate="0.00",
    )

    curves_with_environment = multicurve_analytics_curves(
        discount_curve=discount_curve,
        discount_currency=Currency.USD,
        forward_curve=fallback_forward_curve,
        projection_curves={sofr_3m: projection_curve},
    )
    fallback_curves = AnalyticsCurves(discount_curve=discount_curve, forward_curve=fallback_forward_curve)
    direct_projection_curves = AnalyticsCurves(discount_curve=discount_curve, forward_curve=projection_curve)

    par_with_environment = pricer.par_rate(swap, curves_with_environment)
    par_with_fallback = pricer.par_rate(swap, fallback_curves)
    par_with_direct_projection = pricer.par_rate(swap, direct_projection_curves)

    assert float(par_with_environment) == pytest.approx(float(par_with_direct_projection), abs=1e-12)
    assert float(par_with_environment) > float(par_with_fallback)
