from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.core import Date
from fuggers_py.portfolio import calculate_portfolio_analytics
from fuggers_py.portfolio.bucketing import maturity_bucket_metrics, rating_bucket_metrics, sector_bucket_metrics

from tests.helpers._portfolio_helpers import make_curve, make_portfolio


def test_sector_distribution_weights_sum_to_one() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    buckets = sector_bucket_metrics(make_portfolio(ref), curve=make_curve(ref), settlement_date=ref)
    assert float(sum(bucket.weight for bucket in buckets.values())) == pytest.approx(1.0)


def test_rating_distribution_weights_sum_to_one() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    buckets = rating_bucket_metrics(make_portfolio(ref), curve=make_curve(ref), settlement_date=ref)
    assert float(sum(bucket.weight for bucket in buckets.values())) == pytest.approx(1.0)


def test_maturity_distribution_weights_sum_to_one() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    buckets = maturity_bucket_metrics(make_portfolio(ref), curve=make_curve(ref), settlement_date=ref)
    assert float(sum(bucket.weight for bucket in buckets.values())) == pytest.approx(1.0)


def test_bucket_metrics_are_populated() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    bucket = next(iter(sector_bucket_metrics(make_portfolio(ref), curve=make_curve(ref), settlement_date=ref).values()))
    assert bucket.average_duration is not None
    assert bucket.holding_count > 0


def test_bucket_dv01_sums_to_portfolio_dv01() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    buckets = maturity_bucket_metrics(portfolio, curve=make_curve(ref), settlement_date=ref)
    total = sum((bucket.dv01 for bucket in buckets.values()), Decimal(0))
    metrics = calculate_portfolio_analytics(portfolio, curve=make_curve(ref), settlement_date=ref)
    assert float(total) == pytest.approx(float(metrics.dv01))
