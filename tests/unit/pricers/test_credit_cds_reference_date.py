from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

from fuggers_py._core import Date
from fuggers_py._market.state import AnalyticsCurves
from fuggers_py.credit import CdsPricer, CreditDefaultSwap

from tests.helpers._rates_helpers import flat_curve


@dataclass(frozen=True, slots=True)
class _ReferenceDateCreditCurve:
    reference_date: Date
    hazard_rate: Decimal = Decimal("0.02")

    def survival_probability_at_tenor(self, tenor: float) -> Decimal:
        return Decimal(str(math.exp(-float(self.hazard_rate) * tenor)))


def test_cds_pricer_accepts_credit_curve_with_reference_date_only() -> None:
    reference_date = Date.from_ymd(2026, 1, 2)
    curves = AnalyticsCurves(
        discount_curve=flat_curve(reference_date, "0.00"),
        credit_curve=_ReferenceDateCreditCurve(reference_date),
    )
    cds = CreditDefaultSwap(
        effective_date=reference_date,
        maturity_date=reference_date.add_years(5),
        running_spread=Decimal("0.012"),
        notional=Decimal("1000000"),
    )

    result = CdsPricer().price(cds, curves)

    assert result.protection_leg > Decimal("0")
    assert result.risky_pv01 > Decimal("0")
