from __future__ import annotations

from decimal import Decimal

from fuggers_py.core import Date
from fuggers_py.core import InstrumentId
from fuggers_py.pricers.rates.futures import cheapest_to_deliver, delivery_payoff
from fuggers_py.products.rates.futures import (
    DeliverableBasket,
    DeliverableBond,
    GovernmentBondFuture,
)


def test_delivery_payoff_is_positive_when_the_short_receives_more_than_cash_price() -> None:
    assert delivery_payoff("112.50", "1.00", "112.00") == Decimal("0.5000")


def test_ctd_selection_uses_minimum_gross_basis_equivalently_maximum_delivery_payoff() -> None:
    contract = GovernmentBondFuture(delivery_date=Date.from_ymd(2026, 3, 1))
    basket = DeliverableBasket(
        as_of=Date.from_ymd(2026, 1, 15),
        deliverables=(
            DeliverableBond(
                instrument_id="bond-a",
                issue_date=Date.from_ymd(2020, 3, 1),
                maturity_date=Date.from_ymd(2032, 3, 1),
                coupon_rate="0.03",
                clean_price="112.00",
                published_conversion_factor="1.00",
            ),
            DeliverableBond(
                instrument_id="bond-b",
                issue_date=Date.from_ymd(2020, 3, 1),
                maturity_date=Date.from_ymd(2035, 3, 1),
                coupon_rate="0.04",
                clean_price="118.00",
                published_conversion_factor="1.05",
            ),
            DeliverableBond(
                instrument_id="bond-c",
                issue_date=Date.from_ymd(2020, 3, 1),
                maturity_date=Date.from_ymd(2029, 3, 1),
                coupon_rate="0.025",
                clean_price="107.00",
                published_conversion_factor="0.95",
            ),
        ),
    )

    result = cheapest_to_deliver(contract, basket, "112.50")

    assert result.cheapest_to_deliver == InstrumentId("bond-a")
    assert result.conversion_factor == Decimal("1.00")
    assert result.gross_basis == Decimal("-0.5000")
    assert result.delivery_payoff == Decimal("0.5000")
    assert tuple(candidate.instrument_id for candidate in result.candidates) == (
        InstrumentId("bond-a"),
        InstrumentId("bond-b"),
        InstrumentId("bond-c"),
    )
