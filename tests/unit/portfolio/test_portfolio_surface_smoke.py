from __future__ import annotations

from decimal import Decimal

from fuggers_py.products.bonds.instruments import FixedBond
from fuggers_py.reference.bonds.types import CreditRating, RatingInfo, Sector, SectorInfo, YieldCalculationRules
from fuggers_py.core import Currency, Date, Frequency
from fuggers_py.market.curves import DiscountCurveBuilder
from fuggers_py.portfolio import (
    AnalyticsConfig,
    CashPosition,
    Classification,
    Holding,
    PortfolioBuilder,
    bucket_by_sector,
    calculate_etf_nav,
    calculate_portfolio_analytics,
)


def _curve(ref: Date):
    return (
        DiscountCurveBuilder(reference_date=ref)
        .add_zero_rate(1.0, Decimal("0.03"))
        .add_zero_rate(10.0, Decimal("0.04"))
        .build()
    )


def _holding(ref: Date, *, years: int, coupon: str, label: str, sector: Sector, rating: CreditRating) -> Holding:
    bond = FixedBond.new(
        issue_date=ref,
        maturity_date=ref.add_years(years),
        coupon_rate=Decimal(coupon),
        frequency=Frequency.SEMI_ANNUAL,
        currency=Currency.USD,
        rules=YieldCalculationRules.us_corporate(),
    )
    return Holding(
        instrument=bond,
        quantity=Decimal("2"),
        label=label,
        classification=Classification(sector=sector, rating=rating, currency=Currency.USD),
        rating_info=RatingInfo(rating=rating),
        sector_info=SectorInfo(sector=sector),
        liquidity_score=Decimal("0.8"),
    )


def test_portfolio_builder_and_sector_bucketing() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = (
        PortfolioBuilder()
        .with_currency(Currency.USD)
        .add_position(_holding(ref, years=3, coupon="0.04", label="corp_a", sector=Sector.CORPORATE, rating=CreditRating.BBB))
        .add_position(_holding(ref, years=7, coupon="0.05", label="gov_b", sector=Sector.GOVERNMENT, rating=CreditRating.AA))
        .add_position(CashPosition(amount=Decimal("25"), currency=Currency.USD))
        .build()
    )

    buckets = bucket_by_sector(portfolio)
    assert "CORPORATE" in buckets
    assert "GOVERNMENT" in buckets


def test_calculate_portfolio_analytics_and_etf_nav() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = _curve(ref)
    portfolio = (
        PortfolioBuilder()
        .with_currency(Currency.USD)
        .add_position(_holding(ref, years=3, coupon="0.04", label="corp_a", sector=Sector.CORPORATE, rating=CreditRating.BBB))
        .add_position(_holding(ref, years=7, coupon="0.05", label="gov_b", sector=Sector.GOVERNMENT, rating=CreditRating.AA))
        .build()
    )

    metrics = calculate_portfolio_analytics(portfolio, curve=curve, settlement_date=ref, config=AnalyticsConfig(settlement_date=ref))
    nav = calculate_etf_nav(portfolio, curve=curve, settlement_date=ref, shares_outstanding=Decimal("10"))

    assert metrics.dirty_pv > Decimal("0")
    assert metrics.current_yield >= Decimal("0")
    assert nav > Decimal("0")
