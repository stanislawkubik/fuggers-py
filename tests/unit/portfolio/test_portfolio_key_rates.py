from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._core import Date
from fuggers_py.portfolio import aggregate_key_rate_profile, calculate_portfolio_analytics

from tests.helpers._portfolio_helpers import make_curve, make_portfolio


def test_key_rate_profile_aggregates_holdings() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    profile = aggregate_key_rate_profile(make_portfolio(ref), curve=make_curve(ref), settlement_date=ref)
    assert profile
    assert "2Y" in profile or "3Y" in profile


def test_key_rate_profile_sum_close_to_total_dv01() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    metrics = calculate_portfolio_analytics(portfolio, curve=make_curve(ref), settlement_date=ref)
    partials = sum(metrics.key_rate_profile.values(), Decimal(0))
    assert float(abs(partials)) == pytest.approx(float(abs(metrics.dv01)), rel=0.75)


def test_key_rate_profile_handles_missing_position_krds() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    profile = aggregate_key_rate_profile(make_portfolio(ref), curve=make_curve(ref), settlement_date=ref)
    assert all(isinstance(value, Decimal) for value in profile.values())
