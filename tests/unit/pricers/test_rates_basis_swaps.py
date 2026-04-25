from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._core import Currency, Date, Frequency, PayReceive
from fuggers_py._runtime.state import AnalyticsCurves
from fuggers_py.rates import BasisSwapPricer
from fuggers_py.rates import BasisSwap, FloatingLegSpec, ScheduleDefinition

from tests.helpers._rates_helpers import flat_curve, multicurve_analytics_curves, rate_index


def _basis_swap(reference_date: Date, *, receive_spread: str | Decimal = Decimal("0")) -> BasisSwap:
    return BasisSwap(
        effective_date=reference_date,
        maturity_date=reference_date.add_years(3),
        pay_leg=FloatingLegSpec(
            pay_receive=PayReceive.PAY,
            notional=Decimal("1000000"),
            index_name="SOFR",
            index_tenor="3M",
            currency=Currency.USD,
            schedule=ScheduleDefinition(frequency=Frequency.QUARTERLY),
        ),
        receive_leg=FloatingLegSpec(
            pay_receive=PayReceive.RECEIVE,
            notional=Decimal("1000000"),
            index_name="TERM",
            index_tenor="6M",
            spread=Decimal(str(receive_spread)),
            currency=Currency.USD,
            schedule=ScheduleDefinition(frequency=Frequency.SEMI_ANNUAL),
        ),
        quoted_leg=PayReceive.RECEIVE,
    )


def test_basis_swap_par_spread_is_zero_on_identical_curves() -> None:
    reference_date = Date.from_ymd(2026, 1, 2)
    curve = flat_curve(reference_date, "0.03")
    curves = AnalyticsCurves(discount_curve=curve, forward_curve=curve)
    swap = _basis_swap(reference_date)
    result = BasisSwapPricer().price(swap, curves)

    assert float(result.par_spread) == pytest.approx(0.0, abs=1e-6)
    assert abs(result.present_value) < Decimal("1")


def test_basis_swap_pricer_returns_full_par_spread_for_quoted_leg() -> None:
    reference_date = Date.from_ymd(2026, 1, 2)
    discount_curve = flat_curve(reference_date, "0.02")
    pay_projection_curve = flat_curve(reference_date, "0.03")
    receive_projection_curve = flat_curve(reference_date, "0.04")
    curves = multicurve_analytics_curves(
        discount_curve=discount_curve,
        discount_currency=Currency.USD,
        forward_curve=pay_projection_curve,
        projection_curves={
            rate_index("SOFR", "3M"): pay_projection_curve,
            rate_index("TERM", "6M"): receive_projection_curve,
        },
    )
    swap = _basis_swap(reference_date)
    pricer = BasisSwapPricer()
    result = pricer.price(swap, curves)
    par_swap = _basis_swap(reference_date, receive_spread=result.par_spread)

    assert result.par_spread < Decimal(0)
    assert float(pricer.pv(par_swap, curves)) == pytest.approx(0.0, abs=1e-9)
