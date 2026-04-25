from __future__ import annotations

from decimal import Decimal

from fuggers_py.bonds.types import CreditRating, Sector
from fuggers_py._core import Currency, Date
from fuggers_py.portfolio.types import Classification, Holding, MaturityBucket

from tests.helpers._portfolio_helpers import make_holding


def test_holding_market_value() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    holding = make_holding(
        ref, years=3, coupon="0.04", label="a", sector=Sector.CORPORATE, rating=CreditRating.BBB, quantity="1"
    )
    assert holding.market_value_amount == Decimal("100")


def test_holding_dirty_market_value() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    base = make_holding(
        ref, years=3, coupon="0.04", label="a", sector=Sector.CORPORATE, rating=CreditRating.BBB, quantity="1"
    )
    holding = Holding(
        instrument=base.instrument,
        quantity=base.quantity,
        clean_price=base.clean_price,
        accrued_interest=Decimal("0.5"),
        classification=base.classification,
        rating_info=base.rating_info,
        sector_info=base.sector_info,
    )
    assert holding.dirty_market_value == Decimal("100.5")


def test_holding_base_currency_value() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    base = make_holding(
        ref, years=3, coupon="0.04", label="a", sector=Sector.CORPORATE, rating=CreditRating.BBB, quantity="1"
    )
    holding = Holding(
        instrument=base.instrument,
        quantity=base.quantity,
        clean_price=base.clean_price,
        classification=Classification(currency=Currency.EUR),
        fx_rate=Decimal("1.10"),
    )
    assert holding.base_currency_value == Decimal("110.0")


def test_maturity_bucket_assignment() -> None:
    bucket = MaturityBucket(label="2-5Y", start_years=2.0, end_years=5.0)
    assert bucket.contains(3.0)
    assert not bucket.contains(5.0)


def test_classification_defaults() -> None:
    classification = Classification()
    assert classification.sector is None
    assert classification.custom_fields == {}


def test_credit_rating_ordering() -> None:
    assert CreditRating.A.score() < CreditRating.BB.score()
