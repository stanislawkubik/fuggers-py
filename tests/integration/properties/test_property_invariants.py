from __future__ import annotations

import math
from dataclasses import replace
from decimal import Decimal

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from fuggers_py.measures.functions import (
    clean_price_from_yield,
    effective_convexity,
    effective_duration,
    yield_to_maturity,
)
from fuggers_py.products.bonds.instruments import FixedBond
from fuggers_py.pricers.bonds import BondPricer as BondsBondPricer
from fuggers_py.core import Compounding, Currency, Date, Frequency, Yield
from fuggers_py.market.curves import DiscountCurveBuilder
from fuggers_py.market.curves.discrete import InterpolationMethod
from fuggers_py.math import BisectionSolver, BrentSolver, HybridSolver, SolverConfig
from fuggers_py.portfolio import (
    Portfolio,
    active_weights,
    aggregate_key_rate_profile,
    calculate_portfolio_analytics,
    duration_contributions,
    dv01_contributions,
)
from fuggers_py.portfolio.analytics import PortfolioAnalytics
from fuggers_py.portfolio.bucketing import maturity_bucket_metrics

from tests.helpers._portfolio_helpers import annual_rules, make_benchmark, make_curve, make_portfolio


PROPERTY_SETTINGS = settings(
    max_examples=8,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

LIGHT_PROPERTY_SETTINGS = settings(
    max_examples=16,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

_BPS = Decimal("0.0001")
_TENORS = (0.5, 2.0, 5.0, 10.0)
_GRID = (0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0)

coupon_bps = st.integers(min_value=100, max_value=1200)
yield_bps = st.integers(min_value=100, max_value=1500)
portfolio_scales = st.tuples(
    st.integers(min_value=1, max_value=400),
    st.integers(min_value=1, max_value=400),
    st.integers(min_value=1, max_value=400),
)
benchmark_scales = st.tuples(
    st.integers(min_value=1, max_value=400),
    st.integers(min_value=1, max_value=400),
)
rate_shape = st.tuples(
    st.integers(min_value=1, max_value=300),
    st.integers(min_value=0, max_value=150),
    st.integers(min_value=0, max_value=150),
    st.integers(min_value=0, max_value=150),
)


def _build_bond(*, years: int, coupon_rate: Decimal) -> FixedBond:
    ref = Date.from_ymd(2024, 1, 1)
    return FixedBond.new(
        issue_date=ref,
        maturity_date=ref.add_years(years),
        coupon_rate=coupon_rate,
        frequency=Frequency.ANNUAL,
        currency=Currency.USD,
        rules=annual_rules(),
    )


def _scaled_portfolio(ref: Date, scales: tuple[int, int, int]) -> Portfolio:
    base = make_portfolio(ref)
    positions = [
        replace(position, quantity=Decimal(str(scale)))
        for position, scale in zip(base.positions, scales, strict=True)
    ]
    return Portfolio.new(positions, currency=base.currency)


def _scaled_benchmark(ref: Date, scales: tuple[int, int]) -> Portfolio:
    base = make_benchmark(ref)
    positions = [
        replace(position, quantity=Decimal(str(scale)))
        for position, scale in zip(base.positions, scales, strict=True)
    ]
    return Portfolio.new(positions, currency=base.currency)


def _monotone_zero_rates(shape: tuple[int, int, int, int]) -> list[Decimal]:
    first, second, third, fourth = shape
    running = first
    rates = [Decimal(running) * _BPS]
    for increment in (second, third, fourth):
        running += increment
        rates.append(Decimal(running) * _BPS)
    return rates


@PROPERTY_SETTINGS
@given(years=st.integers(min_value=2, max_value=10), coupon=coupon_bps, ytm=yield_bps)
def test_price_yield_round_trip_property(years: int, coupon: int, ytm: int) -> None:
    ref = Date.from_ymd(2024, 1, 1)
    bond = _build_bond(years=years, coupon_rate=Decimal(coupon) * _BPS)
    expected_yield = Yield.new(Decimal(ytm) * _BPS, Compounding.ANNUAL)

    clean_price = clean_price_from_yield(bond, expected_yield, ref)
    solved_yield = yield_to_maturity(bond, clean_price, ref)
    repriced = clean_price_from_yield(bond, solved_yield, ref)

    assert float(repriced.as_percentage()) == pytest.approx(float(clean_price.as_percentage()), abs=1e-6)


@PROPERTY_SETTINGS
@given(years=st.integers(min_value=3, max_value=12), coupon=coupon_bps, ytm=yield_bps)
def test_effective_duration_and_convexity_match_finite_differences(years: int, coupon: int, ytm: int) -> None:
    ref = Date.from_ymd(2024, 1, 1)
    bump = Decimal("0.0001")
    bond = _build_bond(years=years, coupon_rate=Decimal(coupon) * _BPS)
    base_yield = Yield.new(Decimal(ytm) * _BPS, Compounding.ANNUAL)
    pricer = BondsBondPricer()
    rules = bond.rules()
    engine_yield = float(pricer._yield_to_engine_rate(base_yield, rules=rules))
    dirty_price = Decimal(
        str(
            pricer.engine.dirty_price_from_yield(
                bond.cash_flows(),
                yield_rate=engine_yield,
                settlement_date=ref,
                rules=rules,
            )
        )
    )
    dirty_up = Decimal(
        str(
            pricer.engine.dirty_price_from_yield(
                bond.cash_flows(),
                yield_rate=engine_yield + float(bump),
                settlement_date=ref,
                rules=rules,
            )
        )
    )
    dirty_down = Decimal(
        str(
            pricer.engine.dirty_price_from_yield(
                bond.cash_flows(),
                yield_rate=engine_yield - float(bump),
                settlement_date=ref,
                rules=rules,
            )
        )
    )

    finite_difference_duration = (dirty_down - dirty_up) / (Decimal(2) * dirty_price * bump)
    finite_difference_convexity = (dirty_down + dirty_up - (Decimal(2) * dirty_price)) / (
        dirty_price * (bump**2)
    )

    assert float(effective_duration(bond, base_yield, ref, bump=float(bump))) == pytest.approx(
        float(finite_difference_duration),
        rel=1e-6,
        abs=1e-6,
    )
    assert float(effective_convexity(bond, base_yield, ref, bump=float(bump))) == pytest.approx(
        float(finite_difference_convexity),
        rel=1e-6,
        abs=1e-6,
    )


@LIGHT_PROPERTY_SETTINGS
@given(shape=rate_shape)
def test_discount_factors_are_monotone_for_positive_zero_curves(shape: tuple[int, int, int, int]) -> None:
    ref = Date.from_ymd(2024, 1, 1)
    builder = DiscountCurveBuilder(reference_date=ref)
    for tenor, zero_rate in zip(_TENORS, _monotone_zero_rates(shape), strict=True):
        builder.add_zero_rate(tenor, zero_rate)
    curve = builder.build()

    dfs = [curve.discount_factor_at_tenor(tenor) for tenor in _GRID]
    assert all(df > 0.0 for df in dfs)
    assert all(left >= right for left, right in zip(dfs, dfs[1:], strict=False))


@LIGHT_PROPERTY_SETTINGS
@given(shape=rate_shape)
def test_log_linear_discount_interpolation_keeps_positive_forwards(shape: tuple[int, int, int, int]) -> None:
    ref = Date.from_ymd(2024, 1, 1)
    builder = DiscountCurveBuilder(reference_date=ref).with_interpolation(InterpolationMethod.LOG_LINEAR)
    for tenor, zero_rate in zip(_TENORS, _monotone_zero_rates(shape), strict=True):
        builder.add_pillar(tenor, math.exp(-float(zero_rate) * tenor))
    curve = builder.build()

    forwards = [
        curve.forward_rate_at_tenors(left, right, compounding=Compounding.CONTINUOUS)
        for left, right in zip(_GRID[:-1], _GRID[1:], strict=True)
    ]
    assert all(forward >= -1e-12 for forward in forwards)


@PROPERTY_SETTINGS
@given(portfolio_scale=portfolio_scales, benchmark_scale=benchmark_scales)
def test_active_weights_sum_to_zero_under_quantity_scaling(
    portfolio_scale: tuple[int, int, int],
    benchmark_scale: tuple[int, int],
) -> None:
    ref = Date.from_ymd(2024, 1, 1)
    weights = active_weights(
        _scaled_portfolio(ref, portfolio_scale),
        _scaled_benchmark(ref, benchmark_scale),
        make_curve(ref),
        ref,
    )

    assert float(weights.net_active_weight) == pytest.approx(0.0, abs=1e-12)


@PROPERTY_SETTINGS
@given(scales=portfolio_scales)
def test_contributions_sum_back_to_portfolio_totals(scales: tuple[int, int, int]) -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = _scaled_portfolio(ref, scales)
    curve = make_curve(ref)
    metrics = calculate_portfolio_analytics(portfolio, curve=curve, settlement_date=ref)

    assert float(duration_contributions(portfolio, curve=curve, settlement_date=ref).total) == pytest.approx(
        float(metrics.duration)
    )
    assert float(dv01_contributions(portfolio, curve=curve, settlement_date=ref).total) == pytest.approx(
        float(metrics.dv01)
    )


@PROPERTY_SETTINGS
@given(scales=portfolio_scales)
def test_bucket_totals_sum_back_to_overall_totals(scales: tuple[int, int, int]) -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = _scaled_portfolio(ref, scales)
    curve = make_curve(ref)
    metrics = calculate_portfolio_analytics(portfolio, curve=curve, settlement_date=ref)
    buckets = maturity_bucket_metrics(portfolio, curve=curve, settlement_date=ref)

    assert float(sum((bucket.dirty_pv for bucket in buckets.values()), Decimal(0))) == pytest.approx(
        float(metrics.dirty_pv)
    )
    assert float(sum((bucket.dv01 for bucket in buckets.values()), Decimal(0))) == pytest.approx(
        float(metrics.dv01)
    )


@PROPERTY_SETTINGS
@given(scales=portfolio_scales)
def test_key_rate_profiles_conserve_across_position_aggregation(scales: tuple[int, int, int]) -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = _scaled_portfolio(ref, scales)
    curve = make_curve(ref)
    aggregate = aggregate_key_rate_profile(portfolio, curve=curve, settlement_date=ref)
    position_metrics = PortfolioAnalytics(portfolio).position_metrics(curve, ref)

    manual: dict[str, Decimal] = {}
    for item in position_metrics:
        for tenor, value in item.key_rate_profile.items():
            manual[tenor] = manual.get(tenor, Decimal(0)) + value

    assert set(aggregate.keys()) == set(manual.keys())
    for tenor, value in aggregate.items():
        assert float(value) == pytest.approx(float(manual[tenor]), abs=1e-12)


@LIGHT_PROPERTY_SETTINGS
@given(
    root=st.floats(min_value=0.5, max_value=10.0, allow_nan=False, allow_infinity=False),
    offset=st.floats(min_value=0.1, max_value=0.4, allow_nan=False, allow_infinity=False),
)
def test_bracketed_solvers_converge_inside_the_supplied_interval(root: float, offset: float) -> None:
    left = root * (1.0 - offset)
    right = root * (1.0 + offset)
    midpoint = (left + right) / 2.0
    config = SolverConfig(tolerance=1e-12, max_iterations=200)

    def f(x: float) -> float:
        return x - root

    for solver, args in (
        (BisectionSolver(config=config), (left, right)),
        (BrentSolver(config=config), (left, right)),
        (HybridSolver(config=config), (left, right, midpoint)),
    ):
        result = solver.find_root(f, *args)
        assert result.converged is True
        assert result.residual <= 1e-10
        assert left <= result.root <= right
        assert result.root == pytest.approx(root, abs=1e-8)
