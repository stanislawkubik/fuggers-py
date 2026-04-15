from __future__ import annotations

import math
from decimal import Decimal

import pytest

from fuggers_py.market.curves.credit import bootstrap_credit_curve
from fuggers_py.pricers.credit import CdsPricer
from fuggers_py.products.credit import CreditDefaultSwap
from fuggers_py.core import Date
from fuggers_py.market.curves import CreditCurve
from fuggers_py.market.curves.discrete import DiscreteCurve, ExtrapolationMethod, InterpolationMethod
from fuggers_py.market.curves.value_type import ValueType
from fuggers_py.market.state import AnalyticsCurves
from fuggers_py.market.quotes import CdsQuote
from fuggers_py.reference import CdsReferenceData

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


def test_bootstrap_credit_curve_reprices_par_spread_quotes() -> None:
    reference_date = Date.from_ymd(2026, 1, 2)
    discount_curve = flat_curve(reference_date, "0.03")
    base_credit_curve = _flat_credit_curve(reference_date, "0.02", "0.4")
    analytics_curves = AnalyticsCurves(discount_curve=discount_curve, credit_curve=base_credit_curve)
    pricer = CdsPricer()

    quotes: list[CdsQuote] = []
    for tenor in ("1Y", "3Y", "5Y"):
        maturity_date = reference_date.add_years(int(tenor[0]))
        contract = CreditDefaultSwap(
            effective_date=reference_date,
            maturity_date=maturity_date,
            running_spread=Decimal("0.01"),
            notional=Decimal(1),
            recovery_rate=Decimal("0.4"),
            instrument_id=f"ACME-CDS-{tenor}",
        )
        quotes.append(
            CdsQuote(
                instrument_id=contract.instrument_id,
                par_spread=pricer.par_spread(contract, analytics_curves),
                tenor=tenor,
                recovery_rate=Decimal("0.4"),
            )
        )

    result = bootstrap_credit_curve(
        quotes,
        valuation_date=reference_date,
        discount_curve=discount_curve,
        recovery_rate=Decimal("0.4"),
    )

    for point, quote in zip(result.points, quotes, strict=True):
        assert float(point.fitted_par_spread) == pytest.approx(float(quote.par_spread), abs=1e-8)

    assert float(result.credit_curve.survival_probability(reference_date.add_years(5))) == pytest.approx(
        float(base_credit_curve.survival_probability(reference_date.add_years(5))),
        abs=1e-6,
    )


def test_bootstrap_credit_curve_supports_upfront_quotes_with_reference_coupon() -> None:
    reference_date = Date.from_ymd(2026, 1, 2)
    discount_curve = flat_curve(reference_date, "0.01")
    base_credit_curve = _flat_credit_curve(reference_date, "0.03", "0.4")
    analytics_curves = AnalyticsCurves(discount_curve=discount_curve, credit_curve=base_credit_curve)
    pricer = CdsPricer()
    contract = CreditDefaultSwap(
        effective_date=reference_date,
        maturity_date=reference_date.add_years(5),
        running_spread=Decimal("0.01"),
        notional=Decimal(1),
        recovery_rate=Decimal("0.4"),
        instrument_id="ACME-CDS-5Y-UPFRONT",
    )
    upfront_quote = pricer.upfront(contract, analytics_curves)
    reference = CdsReferenceData(
        instrument_id=contract.instrument_id,
        reference_entity="ACME",
        tenor="5Y",
        coupon=Decimal("0.01"),
        recovery_rate=Decimal("0.4"),
    )

    result = bootstrap_credit_curve(
        [
            CdsQuote(
                instrument_id=contract.instrument_id,
                upfront=upfront_quote,
                tenor="5Y",
                recovery_rate=Decimal("0.4"),
            )
        ],
        valuation_date=reference_date,
        discount_curve=discount_curve,
        reference_data={contract.instrument_id: reference},
    )

    assert len(result.points) == 1
    assert float(result.points[0].fitted_upfront) == pytest.approx(float(upfront_quote), abs=1e-8)
    assert float(result.points[0].fitted_par_spread) == pytest.approx(
        float(pricer.par_spread(contract, analytics_curves)),
        abs=1e-8,
    )
