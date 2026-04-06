from __future__ import annotations

import math
from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py.pricers.credit import CdsPricer
from fuggers_py.products.credit import CreditDefaultSwap, ProtectionSide
from fuggers_py.core import Date
from fuggers_py.market.curves import CreditCurve
from fuggers_py.market.curves.discrete import DiscreteCurve, ExtrapolationMethod, InterpolationMethod
from fuggers_py.market.curves.value_type import ValueType
from fuggers_py.calc import AnalyticsCurves

from tests.helpers._rates_helpers import flat_curve


def _flat_credit_curve(reference_date: Date, hazard_rate: str, recovery_rate: str = "0.4") -> CreditCurve:
    hazard = float(hazard_rate)
    inner = DiscreteCurve(
        reference_date,
        tenors=[1e-8, 10.0],
        values=[1.0, math.exp(-hazard * 10.0)],
        value_type=ValueType.survival_probability(),
        interpolation_method=InterpolationMethod.LOG_LINEAR,
        extrapolation_method=ExtrapolationMethod.FLAT,
    )
    return CreditCurve(inner, recovery_rate=Decimal(recovery_rate))


def test_cds_pricer_exposes_leg_and_upfront_identities() -> None:
    reference_date = Date.from_ymd(2026, 1, 2)
    curves = AnalyticsCurves(
        discount_curve=flat_curve(reference_date, "0.00"),
        credit_curve=_flat_credit_curve(reference_date, "0.02"),
    )
    cds = CreditDefaultSwap(
        effective_date=reference_date,
        maturity_date=reference_date.add_years(5),
        running_spread=Decimal("0.012"),
        notional=Decimal("1000000"),
    )
    pricer = CdsPricer()
    result = pricer.price(cds, curves)

    assert len(cds.premium_periods()) == 20
    assert result.premium_leg == cds.running_spread * result.risky_pv01
    assert result.par_spread == result.protection_leg / result.risky_pv01
    assert result.upfront == (result.protection_leg - result.premium_leg) / cds.notional
    assert result.present_value == pricer.pv(cds, curves)
    assert result.cs01 == result.risky_pv01 * Decimal("0.0001")
    assert result.accrued_on_default > Decimal(0)
    assert result.protection_leg > Decimal(0)


def test_cds_par_spread_tracks_flat_hazard_times_loss_given_default() -> None:
    reference_date = Date.from_ymd(2026, 1, 2)
    hazard_rate = Decimal("0.02")
    recovery_rate = Decimal("0.4")
    curves = AnalyticsCurves(
        discount_curve=flat_curve(reference_date, "0.00"),
        credit_curve=_flat_credit_curve(reference_date, str(hazard_rate), str(recovery_rate)),
    )
    cds = CreditDefaultSwap(
        effective_date=reference_date,
        maturity_date=reference_date.add_years(5),
        running_spread=Decimal("0.0001"),
        notional=Decimal("1000000"),
        recovery_rate=recovery_rate,
    )
    par_spread = CdsPricer().par_spread(cds, curves)

    assert float(par_spread) == pytest.approx(float(hazard_rate * (Decimal(1) - recovery_rate)), abs=2e-4)


def test_selling_protection_flips_signed_measures_only() -> None:
    reference_date = Date.from_ymd(2026, 1, 2)
    curves = AnalyticsCurves(
        discount_curve=flat_curve(reference_date, "0.00"),
        credit_curve=_flat_credit_curve(reference_date, "0.025"),
    )
    buy_cds = CreditDefaultSwap(
        effective_date=reference_date,
        maturity_date=reference_date.add_years(3),
        running_spread=Decimal("0.0100"),
        notional=Decimal("5000000"),
    )
    sell_cds = replace(buy_cds, protection_side=ProtectionSide.SELL)
    pricer = CdsPricer()

    buy_result = pricer.price(buy_cds, curves)
    sell_result = pricer.price(sell_cds, curves)

    assert sell_result.premium_leg == buy_result.premium_leg
    assert sell_result.protection_leg == buy_result.protection_leg
    assert sell_result.risky_pv01 == buy_result.risky_pv01
    assert sell_result.upfront == buy_result.upfront
    assert sell_result.present_value == -buy_result.present_value
    assert sell_result.cs01 == -buy_result.cs01
