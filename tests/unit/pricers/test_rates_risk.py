from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.core import Currency, Date, Frequency
from fuggers_py.market.state import AnalyticsCurves
from fuggers_py.pricers.rates.risk import (
    fra_key_rate_risk,
    fra_pv01,
    key_rate_risk,
    pv01,
    swap_pv01,
)
from fuggers_py.products.rates import (
    FixedFloatSwap,
    FixedLegSpec,
    FloatingLegSpec,
    Fra,
    PayReceive,
    ScheduleDefinition,
)

from tests.helpers._rates_helpers import flat_curve


def _receiver_swap(reference_date: Date) -> FixedFloatSwap:
    return FixedFloatSwap(
        effective_date=reference_date,
        maturity_date=reference_date.add_years(5),
        fixed_leg=FixedLegSpec(
            pay_receive=PayReceive.RECEIVE,
            notional=Decimal("1000000"),
            fixed_rate=Decimal("0.05"),
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


def test_parallel_pv01_is_positive_for_receiver_fixed_swap() -> None:
    reference_date = Date.from_ymd(2026, 1, 2)
    curve = flat_curve(reference_date, "0.03")
    curves = AnalyticsCurves(discount_curve=curve, forward_curve=curve)
    swap = _receiver_swap(reference_date)

    assert swap_pv01(swap, curves) > Decimal(0)
    assert pv01(swap, curves) == swap_pv01(swap, curves)


def test_key_rate_risk_returns_requested_grid_and_has_concentration_near_maturity() -> None:
    reference_date = Date.from_ymd(2026, 1, 2)
    curve = flat_curve(reference_date, "0.03")
    curves = AnalyticsCurves(discount_curve=curve, forward_curve=curve)
    swap = _receiver_swap(reference_date)
    tenor_grid = ("1Y", "2Y", "3Y", "4Y", "5Y")
    exposures = key_rate_risk(swap, curves, tenor_grid=tenor_grid)

    assert set(exposures) == set(tenor_grid)
    assert any(value != Decimal(0) for value in exposures.values())
    assert exposures["4Y"] > exposures["3Y"] > exposures["2Y"] > exposures["1Y"]
    assert exposures["4Y"] > exposures["5Y"]


def test_fra_risk_helpers_return_non_zero_parallel_and_key_rate_risk() -> None:
    reference_date = Date.from_ymd(2026, 1, 2)
    discount_curve = flat_curve(reference_date, "0.03")
    projection_curve = flat_curve(reference_date, "0.04")
    curves = AnalyticsCurves(discount_curve=discount_curve, forward_curve=projection_curve)
    fra = Fra(
        start_date=reference_date.add_months(6),
        end_date=reference_date.add_months(9),
        notional=Decimal("1000000"),
        fixed_rate=Decimal("0.035"),
        pay_receive=PayReceive.RECEIVE,
        currency=Currency.USD,
        index_name="SOFR",
        index_tenor="3M",
    )
    exposures = fra_key_rate_risk(fra, curves, tenor_grid=("6M", "1Y", "2Y"))

    assert fra_pv01(fra, curves) != Decimal(0)
    assert set(exposures) == {"6M", "1Y", "2Y"}
    assert any(value != Decimal(0) for value in exposures.values())
