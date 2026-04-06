from __future__ import annotations

from decimal import Decimal

from fuggers_py.core import Date
from fuggers_py.portfolio import PortfolioBenchmark, estimate_tracking_error

from tests.helpers._portfolio_helpers import make_benchmark, make_curve, make_portfolio


def test_active_weight() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    benchmark = PortfolioBenchmark(make_portfolio(ref), make_benchmark(ref))
    assert any(value != 0 for value in benchmark.active_weights(make_curve(ref), ref).values())


def test_active_weight_underweight() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    active = PortfolioBenchmark(make_portfolio(ref), make_benchmark(ref)).active_weights(make_curve(ref), ref)
    assert any(value < 0 for value in active.values())


def test_active_weights_by_sector() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    active = PortfolioBenchmark(make_portfolio(ref), make_benchmark(ref)).active_weights_by_sector(make_curve(ref), ref)
    assert active


def test_active_weights_by_rating() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    active = PortfolioBenchmark(make_portfolio(ref), make_benchmark(ref)).active_weights_by_rating(make_curve(ref), ref)
    assert active


def test_active_weights_by_holding() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    active = PortfolioBenchmark(make_portfolio(ref), make_benchmark(ref)).active_weights_by_holding(make_curve(ref), ref)
    assert active


def test_overweight_underweight_counts() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    counts = PortfolioBenchmark(make_portfolio(ref), make_benchmark(ref)).overweight_underweight_counts(make_curve(ref), ref)
    assert counts["overweight"] > 0
    assert counts["underweight"] > 0


def test_largest_active_positions() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    positions = PortfolioBenchmark(make_portfolio(ref), make_benchmark(ref)).largest_active_positions(make_curve(ref), ref)
    assert positions


def test_estimate_tracking_error() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    benchmark = PortfolioBenchmark(make_portfolio(ref), make_benchmark(ref))
    assert estimate_tracking_error(benchmark, make_curve(ref), ref) > Decimal("0")


def test_tracking_error_identical() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    benchmark = PortfolioBenchmark(portfolio, portfolio)
    assert estimate_tracking_error(benchmark, make_curve(ref), ref) == Decimal("0")


def test_overweight_underweight_sectors() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    sector_weights = PortfolioBenchmark(make_portfolio(ref), make_benchmark(ref)).active_weights_by_sector(make_curve(ref), ref)
    assert any(value > 0 for value in sector_weights.values())
    assert any(value < 0 for value in sector_weights.values())
