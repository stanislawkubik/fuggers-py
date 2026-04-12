from __future__ import annotations

from decimal import Decimal

import fuggers_py.core as core
from fuggers_py.core import CashFlow, Date
from fuggers_py.core import traits as core_traits


class DummyCurve:
    def __init__(self, df_end: Decimal) -> None:
        self._df_end = df_end

    def discount_factor(self, date: Date) -> Decimal:
        return self._df_end


def test_discountable_present_value_default() -> None:
    cf = CashFlow.coupon(Date.parse("2026-01-01"), "100")
    curve = DummyCurve(df_end=Decimal("0.95"))
    assert cf.present_value(curve) == Decimal("95.00")


def test_old_yieldcurve_trait_is_removed() -> None:
    assert not hasattr(core, "YieldCurve")
    assert not hasattr(core_traits, "YieldCurve")
