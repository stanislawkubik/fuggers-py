from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.products.bonds.instruments import FixedBondBuilder
from fuggers_py.pricers.bonds.risk import RiskMetrics
from fuggers_py.core import Compounding, Date, Frequency, Yield


def test_risk_metrics_signs_are_sensible() -> None:
    bond = (
        FixedBondBuilder.new()
        .with_issue_date(Date.from_ymd(2024, 1, 1))
        .with_maturity_date(Date.from_ymd(2026, 1, 1))
        .with_coupon_rate(Decimal("0.05"))
        .with_frequency(Frequency.SEMI_ANNUAL)
        .build()
    )

    settlement = Date.from_ymd(2024, 1, 1)
    ytm = Yield.new(Decimal("0.05"), Compounding.SEMI_ANNUAL)

    metrics = RiskMetrics.from_bond(bond, ytm, settlement)
    assert metrics.modified_duration > 0
    assert metrics.convexity > 0
    assert metrics.dv01 > 0
    assert metrics.modified_duration < Decimal(50)


def test_risk_metrics_are_compounding_invariant_for_equivalent_yield() -> None:
    bond = (
        FixedBondBuilder.new()
        .with_issue_date(Date.from_ymd(2024, 1, 1))
        .with_maturity_date(Date.from_ymd(2026, 1, 1))
        .with_coupon_rate(Decimal("0.05"))
        .with_frequency(Frequency.SEMI_ANNUAL)
        .build()
    )

    settlement = Date.from_ymd(2024, 1, 1)
    ytm_sa = Yield.new(Decimal("0.05"), Compounding.SEMI_ANNUAL)
    ytm_ann = ytm_sa.convert_to(Compounding.ANNUAL)

    m1 = RiskMetrics.from_bond(bond, ytm_sa, settlement)
    m2 = RiskMetrics.from_bond(bond, ytm_ann, settlement)

    assert float(m1.modified_duration) == pytest.approx(float(m2.modified_duration), rel=1e-10, abs=1e-12)
    assert float(m1.dv01) == pytest.approx(float(m2.dv01), rel=1e-10, abs=1e-12)
