from __future__ import annotations

from decimal import Decimal

from fuggers_py.core import CashFlow, Compounding, Date, Yield
from fuggers_py.core.traits import YieldCurve


class DummyCurve(YieldCurve):
    def __init__(self, ref: Date, df_end: Decimal) -> None:
        self._ref = ref
        self._df_end = df_end

    def reference_date(self) -> Date:
        return self._ref

    def discount_factor(self, date: Date) -> Decimal:
        if date == self._ref:
            return Decimal(1)
        return self._df_end

    def zero_rate(self, date: Date) -> Yield:
        return Yield.new(Decimal("0.0"), Compounding.ANNUAL)

    def max_date(self) -> Date:
        return self._ref.add_years(100)


def test_discountable_present_value_default() -> None:
    cf = CashFlow.coupon(Date.parse("2026-01-01"), "100")
    curve = DummyCurve(ref=Date.parse("2025-01-01"), df_end=Decimal("0.95"))
    assert cf.present_value(curve) == Decimal("95.00")


def test_yieldcurve_forward_rate_default() -> None:
    start = Date.parse("2025-01-01")
    end = Date.parse("2026-01-01")  # 365 days
    curve = DummyCurve(ref=start, df_end=Decimal("0.95"))
    fwd = curve.forward_rate(start, end)
    assert abs(fwd - (Decimal(1) / Decimal("0.95") - Decimal(1))) < Decimal("1e-12")

