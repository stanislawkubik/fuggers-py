from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from fuggers_py._core import Currency, Date, Frequency
from fuggers_py._products.bonds.instruments import FloatingRateNoteBuilder
from fuggers_py._reference.bonds.types import RateIndex
from fuggers_py._core import YieldCalculationRules


def _quarterly_treasury_rules() -> YieldCalculationRules:
    return replace(YieldCalculationRules.us_treasury(), frequency=Frequency.QUARTERLY)


@dataclass(frozen=True, slots=True)
class _ReferenceDateForwardCurve:
    reference_date: Date
    rate: Decimal = Decimal("0.05")

    def forward_rate_at(self, tenor: float) -> Decimal:
        return self.rate


def test_period_coupon_accepts_reference_date_forward_curve_without_date_method() -> None:
    ref = Date.from_ymd(2024, 1, 10)
    note = (
        FloatingRateNoteBuilder.new()
        .with_issue_date(ref.add_months(-3))
        .with_maturity_date(ref.add_years(2))
        .with_index(RateIndex.SOFR)
        .with_frequency(Frequency.QUARTERLY)
        .with_currency(Currency.USD)
        .with_quoted_spread(Decimal("0.0025"))
        .with_rules(_quarterly_treasury_rules())
        .with_current_reference_rate(Decimal("0.0520"))
        .build()
    )
    start, end = note.schedule().unadjusted_dates[:2]

    coupon = note.period_coupon(start, end, forward_curve=_ReferenceDateForwardCurve(ref))

    assert coupon > Decimal("0")
