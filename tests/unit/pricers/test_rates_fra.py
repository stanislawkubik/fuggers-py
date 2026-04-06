from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.core import Currency, Date
from fuggers_py.calc import AnalyticsCurves
from fuggers_py.pricers.rates import FraPricer
from fuggers_py.products.rates import Fra, PayReceive

from tests.helpers._rates_helpers import flat_curve, multicurve_analytics_curves, rate_index


def test_fra_pricer_forward_rate_and_pv_follow_start_settled_formula() -> None:
    reference_date = Date.from_ymd(2026, 1, 2)
    start_date = reference_date.add_months(6)
    end_date = reference_date.add_months(9)
    discount_curve = flat_curve(reference_date, "0.03")
    projection_curve = flat_curve(reference_date, "0.04")
    curves = AnalyticsCurves(discount_curve=discount_curve, forward_curve=projection_curve)
    fra = Fra(
        start_date=start_date,
        end_date=end_date,
        notional=Decimal("1000000"),
        fixed_rate=Decimal("0.035"),
        pay_receive=PayReceive.RECEIVE,
        currency=Currency.USD,
        index_name="SOFR",
        index_tenor="3M",
    )
    pricer = FraPricer()
    tau = fra.year_fraction()
    expected_forward = (projection_curve.discount_factor(start_date) / projection_curve.discount_factor(end_date) - Decimal(1)) / tau
    expected_pv = (
        fra.notional
        * (expected_forward - fra.fixed_rate)
        * tau
        / (Decimal(1) + expected_forward * tau)
        * discount_curve.discount_factor(start_date)
    )

    result = pricer.price(fra, curves)

    assert result.forward_rate == expected_forward
    assert result.present_value == expected_pv
    assert result.discount_factor == discount_curve.discount_factor(start_date)
    assert pricer.pv(
        Fra(
            start_date=start_date,
            end_date=end_date,
            notional=Decimal("1000000"),
            fixed_rate=Decimal("0.035"),
            pay_receive=PayReceive.PAY,
            currency=Currency.USD,
            index_name="SOFR",
            index_tenor="3M",
        ),
        curves,
    ) == -expected_pv


def test_fra_pricer_prefers_multicurve_environment_when_present() -> None:
    reference_date = Date.from_ymd(2026, 1, 2)
    discount_curve = flat_curve(reference_date, "0.03")
    fallback_forward_curve = flat_curve(reference_date, "0.03")
    projection_curve = flat_curve(reference_date, "0.04")
    sofr_3m = rate_index("SOFR", "3M")
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
    pricer = FraPricer()

    curves_with_environment = multicurve_analytics_curves(
        discount_curve=discount_curve,
        discount_currency=Currency.USD,
        forward_curve=fallback_forward_curve,
        projection_curves={sofr_3m: projection_curve},
    )
    fallback_curves = AnalyticsCurves(discount_curve=discount_curve, forward_curve=fallback_forward_curve)
    direct_projection_curves = AnalyticsCurves(discount_curve=discount_curve, forward_curve=projection_curve)

    assert float(pricer.forward_rate(fra, curves_with_environment)) == pytest.approx(
        float(pricer.forward_rate(fra, direct_projection_curves)),
        abs=1e-12,
    )
    assert float(pricer.forward_rate(fra, curves_with_environment)) > float(pricer.forward_rate(fra, fallback_curves))
