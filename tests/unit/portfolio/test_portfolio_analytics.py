from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.measures.pricing import BondPricer
from fuggers_py.measures.risk import BondRiskCalculator
from fuggers_py.products.bonds.instruments import FixedBond, ZeroCouponBond
from fuggers_py.core import Date, Frequency
from fuggers_py.market.curves import DiscountCurveBuilder
from fuggers_py.portfolio import Bucketing, Portfolio, PortfolioAnalytics, Position, Stress


def _curve(ref: Date):
    return (
        DiscountCurveBuilder(reference_date=ref)
        .add_zero_rate(1.0, Decimal("0.03"))
        .add_zero_rate(10.0, Decimal("0.04"))
        .build()
    )


def _portfolio(ref: Date) -> Portfolio:
    bond_1 = FixedBond.new(issue_date=ref, maturity_date=ref.add_years(3), coupon_rate=Decimal("0.04"), frequency=Frequency.SEMI_ANNUAL)
    bond_2 = FixedBond.new(issue_date=ref, maturity_date=ref.add_years(7), coupon_rate=Decimal("0.05"), frequency=Frequency.SEMI_ANNUAL)
    zero = ZeroCouponBond(_issue_date=ref, _maturity_date=ref.add_years(2))
    return Portfolio.new(
        [
            Position(bond_1, quantity=Decimal("2"), label="bond_1"),
            Position(bond_2, quantity=Decimal("1.5"), label="bond_2"),
            Position(zero, quantity=Decimal("3"), label="zero"),
        ],
        currency=bond_1.currency(),
    )


def test_portfolio_pv_is_sum_of_positions() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = _curve(ref)
    portfolio = _portfolio(ref)
    analytics = PortfolioAnalytics(portfolio)
    pricer = BondPricer()

    expected = Decimal(0)
    for position in portfolio.positions:
        expected += pricer.price_from_curve(position.instrument, curve, ref).dirty.as_percentage() * position.quantity

    assert float(analytics.metrics(curve, ref).dirty_pv) == pytest.approx(float(expected), abs=1e-8)


def test_portfolio_duration_is_value_weighted_average() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = _curve(ref)
    portfolio = _portfolio(ref)
    analytics = PortfolioAnalytics(portfolio)
    pricer = BondPricer()

    total_value = Decimal(0)
    weighted_duration = Decimal(0)
    for position in portfolio.positions:
        priced = pricer.price_from_curve(position.instrument, curve, ref)
        ytm = pricer.yield_to_maturity(position.instrument, priced.clean, ref)
        risk = BondRiskCalculator(position.instrument, ytm, ref).all_metrics()
        dirty_value = priced.dirty.as_percentage() * position.quantity
        total_value += dirty_value
        weighted_duration += risk.modified_duration * dirty_value

    expected = weighted_duration / total_value
    assert float(analytics.metrics(curve, ref).duration) == pytest.approx(float(expected), rel=1e-10)


def test_portfolio_dv01_approximates_parallel_shift_pv_change() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = _curve(ref)
    portfolio = _portfolio(ref)
    analytics = PortfolioAnalytics(portfolio)
    stress = Stress(portfolio)

    base = analytics.metrics(curve, ref)
    stressed = stress.parallel_shift(curve, ref, bump_bps=Decimal("10"))

    assert float(stressed.actual_change) == pytest.approx(float(-(base.dv01 * Decimal("10"))), rel=0.15)


def test_portfolio_bucket_dv01_sums_to_total_dv01() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = _curve(ref)
    portfolio = _portfolio(ref)
    analytics = PortfolioAnalytics(portfolio)
    buckets = Bucketing(portfolio).bucket_dv01(curve, ref)

    bucket_sum = sum((bucket.dv01 for bucket in buckets), Decimal(0))
    assert float(bucket_sum) == pytest.approx(float(analytics.metrics(curve, ref).dv01), rel=1e-10)
