from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py._core import Currency, Date
from fuggers_py.portfolio import Portfolio
from fuggers_py.portfolio.bucketing.custom import (
    bucket_by_country,
    bucket_by_currency,
    bucket_by_custom_field,
    bucket_by_issuer,
    bucket_by_region,
)
from fuggers_py.portfolio.contribution import attribution_summary, weights_sum_check
from fuggers_py.portfolio.etf.sec import calculate_distribution_yield, etf_compliance_checks

from tests.helpers._portfolio_helpers import make_curve, make_holding, make_portfolio


def test_bucket_by_custom_field_prefers_position_then_classification_then_unknown() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    direct = replace(
        make_holding(
            ref,
            years=2,
            coupon="0.04",
            label="direct",
            sector=make_portfolio(ref).positions[0].classification.sector,
            rating=make_portfolio(ref).positions[0].classification.rating,
        ),
        custom_fields={"desk": "ALPHA"},
    )
    fallback_base = make_holding(
        ref,
        years=4,
        coupon="0.045",
        label="fallback",
        sector=make_portfolio(ref).positions[1].classification.sector,
        rating=make_portfolio(ref).positions[1].classification.rating,
    )
    fallback = replace(
        fallback_base,
        classification=replace(fallback_base.classification, custom_fields={"desk": "BETA"}),
    )
    unknown = replace(
        make_holding(
            ref,
            years=6,
            coupon="0.05",
            label="unknown",
            sector=make_portfolio(ref).positions[2].classification.sector,
            rating=make_portfolio(ref).positions[2].classification.rating,
        ),
        classification=None,
    )
    portfolio = Portfolio.new([direct, fallback, unknown], currency=Currency.USD)

    buckets = bucket_by_custom_field(portfolio, "desk")

    assert [position.name() for position in buckets["ALPHA"]] == ["direct"]
    assert [position.name() for position in buckets["BETA"]] == ["fallback"]
    assert [position.name() for position in buckets["UNKNOWN"]] == ["unknown"]


def test_bucket_by_attribute_helpers_use_unknown_bucket_for_missing_classification() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    base = make_holding(
        ref,
        years=3,
        coupon="0.04",
        label="classified",
        sector=make_portfolio(ref).positions[0].classification.sector,
        rating=make_portfolio(ref).positions[0].classification.rating,
    )
    classified = replace(
        base,
        classification=replace(
            base.classification,
            country="US",
            region="NA",
            issuer="classified_issuer",
            currency=Currency.USD,
        ),
    )
    unclassified = replace(classified, label="unclassified", id="unclassified", classification=None)
    portfolio = Portfolio.new([classified, unclassified], currency=Currency.USD)

    assert sorted(bucket_by_country(portfolio)) == ["UNKNOWN", "US"]
    assert sorted(bucket_by_currency(portfolio)) == ["UNKNOWN", Currency.USD]
    assert sorted(bucket_by_issuer(portfolio)) == ["UNKNOWN", "classified_issuer"]
    assert sorted(bucket_by_region(portfolio)) == ["NA", "UNKNOWN"]


def test_attribution_summary_handles_zero_total_portfolio_without_division_errors() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    base = make_portfolio(ref)
    zero_positions = [replace(position, quantity=Decimal("0")) for position in base.positions]
    zero_portfolio = Portfolio.new(zero_positions, currency=base.currency)

    attribution = attribution_summary(zero_portfolio, curve=make_curve(ref), settlement_date=ref)

    assert attribution.total_pv_pct == Decimal(0)
    assert attribution.total_dv01_pct == Decimal(0)
    assert all(entry.pv_pct == 0 for entry in attribution.entries)
    assert all(entry.dv01_pct == 0 for entry in attribution.entries)


def test_weights_sum_check_matches_normal_and_zero_weight_portfolios() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    normal_portfolio = make_portfolio(ref)
    zero_positions = [replace(position, quantity=Decimal("0")) for position in normal_portfolio.positions]
    zero_portfolio = Portfolio.new(zero_positions, currency=normal_portfolio.currency)
    curve = make_curve(ref)

    assert float(weights_sum_check(normal_portfolio, curve=curve, settlement_date=ref)) == pytest.approx(1.0)
    assert weights_sum_check(zero_portfolio, curve=curve, settlement_date=ref) == Decimal(0)


def test_etf_sec_helpers_enforce_tolerance_and_market_price_domains() -> None:
    checks_inside_tolerance = etf_compliance_checks(
        holdings_weight_sum=Decimal("1.00009"),
        max_issuer_weight=Decimal("0.25"),
    )
    checks_outside_tolerance = etf_compliance_checks(
        holdings_weight_sum=Decimal("1.00011"),
        max_issuer_weight=Decimal("0.2501"),
    )

    assert checks_inside_tolerance.weights_sum_to_one is True
    assert checks_inside_tolerance.issuer_limit_ok is True
    assert checks_outside_tolerance.weights_sum_to_one is False
    assert checks_outside_tolerance.issuer_limit_ok is False

    with pytest.raises(ValueError):
        calculate_distribution_yield(Decimal("4.0"), Decimal("0"))
