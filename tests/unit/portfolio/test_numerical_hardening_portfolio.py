from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._core import Date
from fuggers_py.portfolio import calculate_portfolio_analytics
from fuggers_py.portfolio.contribution import attribution_summary
from fuggers_py.portfolio.etf.nav import calculate_etf_nav, premium_discount_stats
from fuggers_py.portfolio.etf.sec import (
    SecYieldInput,
    approximate_sec_yield,
    calculate_sec_yield,
    etf_compliance_checks,
)

from tests.helpers._portfolio_helpers import make_curve, make_portfolio


def test_calculate_sec_yield_requires_positive_net_assets() -> None:
    with pytest.deprecated_call():
        with pytest.raises(ValueError):
            calculate_sec_yield(Decimal("1.0"), Decimal("0"))


def test_legacy_sec_yield_path_warns_and_matches_approximation() -> None:
    with pytest.deprecated_call():
        legacy = calculate_sec_yield(Decimal("1.0"), Decimal("20.0"))

    assert legacy == approximate_sec_yield(Decimal("1.0"), Decimal("20.0"))


def test_standardized_sec_yield_requires_positive_typed_inputs() -> None:
    with pytest.raises(ValueError):
        calculate_sec_yield(
            SecYieldInput(
                net_investment_income=Decimal("1.0"),
                average_shares_outstanding=Decimal("0"),
                max_offering_price=Decimal("20.0"),
            )
        )

    with pytest.raises(ValueError):
        calculate_sec_yield(
            SecYieldInput(
                net_investment_income=Decimal("1.0"),
                average_shares_outstanding=Decimal("10"),
                max_offering_price=Decimal("0"),
            )
        )


def test_etf_compliance_checks_validate_issuer_weight_domain() -> None:
    with pytest.raises(ValueError):
        etf_compliance_checks(holdings_weight_sum=Decimal("1"), max_issuer_weight=Decimal("-0.01"))


def test_premium_discount_stats_are_typed_and_attribute_accessible() -> None:
    stats = premium_discount_stats(Decimal("100"), Decimal("101"))

    assert stats.premium_discount == Decimal("0.01")
    assert stats.premium_discount_bps == Decimal("100.00")
    assert stats.premium_discount_pct == Decimal("1.00")


def test_calculate_etf_nav_requires_positive_shares_outstanding() -> None:
    ref = Date.from_ymd(2024, 1, 1)

    with pytest.raises(ValueError):
        calculate_etf_nav(make_portfolio(ref), curve=make_curve(ref), settlement_date=ref, shares_outstanding=Decimal("0"))


def test_attribution_summary_reconciles_to_portfolio_duration() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = make_curve(ref)
    portfolio = make_portfolio(ref)

    attribution = attribution_summary(portfolio, curve=curve, settlement_date=ref)
    analytics = calculate_portfolio_analytics(portfolio, curve=curve, settlement_date=ref)

    assert float(attribution.total_pv_pct) == pytest.approx(1.0, abs=1e-12)
    assert attribution.total_duration_contribution == analytics.duration
