from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._core import Date
from fuggers_py.portfolio import calculate_portfolio_analytics
from fuggers_py.portfolio.contribution import (
    duration_contributions,
    dv01_contributions,
    spread_contributions,
    top_contributors,
)

from tests.helpers._portfolio_helpers import make_curve, make_portfolio


def test_duration_contributions_sum_to_portfolio_duration() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    contributions = duration_contributions(portfolio, curve=make_curve(ref), settlement_date=ref)
    total = sum((entry["duration_contribution"] for entry in contributions), Decimal(0))
    metrics = calculate_portfolio_analytics(portfolio, curve=make_curve(ref), settlement_date=ref)
    assert float(total) == pytest.approx(float(metrics.duration))


def test_dv01_contributions_sum_to_portfolio_dv01() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    contributions = dv01_contributions(portfolio, curve=make_curve(ref), settlement_date=ref)
    total = sum((entry["dv01_contribution"] for entry in contributions), Decimal(0))
    metrics = calculate_portfolio_analytics(portfolio, curve=make_curve(ref), settlement_date=ref)
    assert float(total) == pytest.approx(float(metrics.dv01))


def test_spread_contributions_sum_when_all_inputs_present() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    contributions = spread_contributions(make_portfolio(ref), curve=make_curve(ref), settlement_date=ref)
    assert sum((entry["spread_contribution"] for entry in contributions), Decimal(0)) >= Decimal("0")


def test_top_contributors_sorted_by_absolute_value() -> None:
    entries = [
        {"name": "a", "dv01_contribution": Decimal("1")},
        {"name": "b", "dv01_contribution": Decimal("-3")},
        {"name": "c", "dv01_contribution": Decimal("2")},
    ]
    result = top_contributors(entries, value_key="dv01_contribution", absolute=True)
    assert [entry["name"] for entry in result] == ["b", "c", "a"]
