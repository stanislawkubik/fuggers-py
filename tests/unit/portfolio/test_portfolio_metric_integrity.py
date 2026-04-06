from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py.core import Date
from fuggers_py.portfolio import Portfolio, PortfolioAnalytics
from fuggers_py.portfolio.types import HoldingAnalytics

from tests.helpers._portfolio_helpers import make_curve, make_holding, make_portfolio


def _precomputed_analytics(*, name: str, clean_value: str, g_spread: str | None) -> HoldingAnalytics:
    clean = Decimal(clean_value)
    return HoldingAnalytics(
        name=name,
        market_value=clean,
        dirty_value=clean,
        clean_value=clean,
        accrued_value=Decimal(0),
        duration=Decimal("4.5"),
        convexity=Decimal("0.25"),
        dv01=Decimal("0.09"),
        ytm=Decimal("0.041"),
        current_yield=Decimal("0.038"),
        best_yield=Decimal("0.041"),
        z_spread=Decimal("0.012"),
        oas=None,
        g_spread=None if g_spread is None else Decimal(g_spread),
        i_spread=None,
        asw=None,
        best_spread=Decimal("0.012"),
        spread_duration=Decimal("3.8"),
        cs01=Decimal("0.038"),
        modified_duration=Decimal("4.5"),
        effective_duration=Decimal("4.5"),
        macaulay_duration=Decimal("4.7"),
        effective_convexity=Decimal("0.25"),
        liquidity_score=Decimal("0.85"),
        weighted_average_life=Decimal("4.0"),
        coupon=Decimal("0.04"),
    )


def test_position_and_portfolio_spreads_do_not_alias_z_spread() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = make_curve(ref)
    analytics = PortfolioAnalytics(make_portfolio(ref))

    positions = analytics.position_metrics(curve, ref)
    metrics = analytics.metrics(curve, ref)

    assert metrics.z_spread > Decimal(0)
    assert metrics.g_spread is None
    assert metrics.i_spread is None
    assert metrics.asw is None
    assert metrics.best_spread == metrics.z_spread
    assert all(position.g_spread is None for position in positions)
    assert all(position.i_spread is None for position in positions)
    assert all(position.asw is None for position in positions)
    assert all(position.best_spread == position.z_spread for position in positions)


def test_optional_spreads_are_aggregated_without_zero_filling() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    base_portfolio = make_portfolio(ref)
    first, second, *_ = base_portfolio.positions
    portfolio = Portfolio.new(
        [
            replace(first, analytics=_precomputed_analytics(name=first.name(), clean_value="100", g_spread="0.015")),
            replace(second, analytics=_precomputed_analytics(name=second.name(), clean_value="100", g_spread=None)),
        ],
        currency=base_portfolio.currency,
    )

    metrics = PortfolioAnalytics(portfolio).metrics(curve=None, settlement_date=ref)

    assert metrics.g_spread == Decimal("0.015")
    assert metrics.i_spread is None
    assert metrics.asw is None


def test_spread_failures_are_not_silently_masked(monkeypatch: pytest.MonkeyPatch) -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    curve = make_curve(ref)

    def _boom(*args, **kwargs):
        raise RuntimeError("spread failure should surface")

    monkeypatch.setattr("fuggers_py.portfolio._analytics_utils.z_spread_from_curve", _boom)

    with pytest.raises(RuntimeError, match="spread failure should surface"):
        PortfolioAnalytics(portfolio).metrics(curve, ref)
