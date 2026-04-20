from __future__ import annotations

from decimal import Decimal

from fuggers_py._core import Date
from fuggers_py.funding import RepoTrade, futures_invoice_amount, implied_repo_rate, implied_repo_rate_from_trade


def test_futures_invoice_amount_and_implied_repo_rate_from_primitives() -> None:
    start = Date.from_ymd(2026, 1, 1)
    end = start.add_days(180)

    assert futures_invoice_amount(futures_price="125", conversion_factor="0.8") == Decimal("100")
    assert futures_invoice_amount(futures_price="125", conversion_factor="0.8", face_amount="1000") == Decimal("1000")

    rate = implied_repo_rate(
        spot_price=Decimal("100"),
        futures_price=Decimal("125"),
        conversion_factor=Decimal("0.8"),
        start_date=start,
        end_date=end,
        coupon_income=Decimal("2"),
    )

    assert rate == Decimal("0.04")


def test_implied_repo_rate_from_repo_trade_uses_trade_dates_and_day_count() -> None:
    start = Date.from_ymd(2026, 1, 1)
    end = start.add_days(180)
    trade = RepoTrade(
        start_date=start,
        end_date=end,
        rate=Decimal("0.03"),
        collateral_price=Decimal("100"),
        haircut=Decimal("0"),
        notional=Decimal("100"),
    )

    assert implied_repo_rate_from_trade(
        trade,
        futures_price=Decimal("125"),
        conversion_factor=Decimal("0.8"),
        coupon_income=Decimal("2"),
    ) == Decimal("0.04")
