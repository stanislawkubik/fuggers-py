from __future__ import annotations

from decimal import Decimal

from fuggers_py._reference.bonds.types import CreditRating, Sector
from fuggers_py._core import Currency, Date
from fuggers_py.portfolio import (
    FallenAngelRisk,
    MigrationRisk,
    PortfolioBuilder,
    QualityTiers,
    RisingStarRisk,
    calculate_credit_quality,
    calculate_migration_risk,
)

from tests.helpers._portfolio_helpers import make_holding


def test_credit_quality_empty() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = PortfolioBuilder().with_currency(Currency.USD).build()
    quality = calculate_credit_quality(portfolio)
    assert quality.distribution == {}


def test_credit_quality_ig_portfolio() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = (
        PortfolioBuilder()
        .with_currency(Currency.USD)
        .add_holding(
            make_holding(ref, years=2, coupon="0.03", label="ig_a", sector=Sector.GOVERNMENT, rating=CreditRating.AA)
        )
        .add_holding(
            make_holding(ref, years=5, coupon="0.04", label="ig_b", sector=Sector.CORPORATE, rating=CreditRating.A)
        )
        .build()
    )
    quality = calculate_credit_quality(portfolio)
    assert quality.investment_grade_weight == Decimal("1")


def test_credit_quality_mixed_portfolio() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = (
        PortfolioBuilder()
        .with_currency(Currency.USD)
        .add_holding(
            make_holding(ref, years=4, coupon="0.04", label="bbb", sector=Sector.CORPORATE, rating=CreditRating.BBB)
        )
        .add_holding(
            make_holding(ref, years=6, coupon="0.06", label="bb", sector=Sector.INDUSTRIALS, rating=CreditRating.BB)
        )
        .build()
    )
    quality = calculate_credit_quality(portfolio)
    assert quality.investment_grade_weight > Decimal("0")
    assert quality.high_yield_weight > Decimal("0")


def test_crossover_risk() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = (
        PortfolioBuilder()
        .with_currency(Currency.USD)
        .add_holding(
            make_holding(ref, years=4, coupon="0.04", label="bbb", sector=Sector.CORPORATE, rating=CreditRating.BBB)
        )
        .add_holding(
            make_holding(ref, years=6, coupon="0.06", label="bb", sector=Sector.INDUSTRIALS, rating=CreditRating.BB)
        )
        .build()
    )
    quality = calculate_credit_quality(portfolio)
    assert quality.crossover_weight == Decimal("1")


def test_quality_tiers() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = (
        PortfolioBuilder()
        .with_currency(Currency.USD)
        .add_holding(
            make_holding(ref, years=4, coupon="0.04", label="ig", sector=Sector.CORPORATE, rating=CreditRating.A)
        )
        .add_holding(
            make_holding(ref, years=6, coupon="0.08", label="hy", sector=Sector.INDUSTRIALS, rating=CreditRating.B)
        )
        .build()
    )
    tiers = calculate_credit_quality(portfolio).quality_tiers
    assert isinstance(tiers, QualityTiers)
    assert tiers.investment_grade > Decimal("0")
    assert tiers.high_yield > Decimal("0")


def test_migration_risk() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = (
        PortfolioBuilder()
        .with_currency(Currency.USD)
        .add_holding(
            make_holding(ref, years=4, coupon="0.04", label="bbb", sector=Sector.CORPORATE, rating=CreditRating.BBB)
        )
        .add_holding(
            make_holding(ref, years=6, coupon="0.06", label="bb", sector=Sector.INDUSTRIALS, rating=CreditRating.BB)
        )
        .build()
    )
    migration = calculate_migration_risk(portfolio)
    assert isinstance(migration, MigrationRisk)
    assert isinstance(migration.fallen_angel, FallenAngelRisk)
    assert isinstance(migration.rising_star, RisingStarRisk)
    assert migration.fallen_angel_risk > Decimal("0")
    assert migration.rising_star_risk > Decimal("0")
