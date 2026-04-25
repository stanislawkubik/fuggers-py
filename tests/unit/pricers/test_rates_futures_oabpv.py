from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from fuggers_py._core import Date
from fuggers_py._core import InstrumentId
from fuggers_py.rates.futures import (
    NoDeliveryOptionModel,
    YieldGridCTDSwitchModel,
    fair_futures_price,
    oabpv,
)
from fuggers_py.rates.futures import (
    DeliverableBasket,
    DeliverableBond,
    GovernmentBondFuture,
)


def _switching_contract_and_basket() -> tuple[GovernmentBondFuture, DeliverableBasket]:
    as_of = Date.from_ymd(2025, 12, 31)
    contract = GovernmentBondFuture(delivery_date=Date.from_ymd(2026, 3, 1), standard_coupon_rate="0.06")

    long_template = DeliverableBond(
        instrument_id="long-duration",
        issue_date=Date.from_ymd(2020, 3, 1),
        maturity_date=Date.from_ymd(2040, 3, 1),
        coupon_rate="0.02",
        clean_price="100",
    )
    short_template = DeliverableBond(
        instrument_id="short-duration",
        issue_date=Date.from_ymd(2021, 3, 1),
        maturity_date=Date.from_ymd(2031, 3, 1),
        coupon_rate="0.06",
        clean_price="100",
    )

    long_price = long_template.price_from_yield(Decimal("0.04"), as_of)
    short_price = short_template.price_from_yield(Decimal("0.04"), as_of)
    target_equivalent = Decimal("105")

    long_bond = replace(
        long_template,
        clean_price=long_price,
        published_conversion_factor=long_price / target_equivalent,
    )
    short_bond = replace(
        short_template,
        clean_price=short_price,
        published_conversion_factor=short_price / target_equivalent,
    )
    basket = DeliverableBasket(as_of=as_of, deliverables=(long_bond, short_bond))
    return contract, basket


def test_yield_grid_delivery_option_adjustment_is_positive_when_ctd_switches() -> None:
    contract, basket = _switching_contract_and_basket()
    model = YieldGridCTDSwitchModel((Decimal("-100"), Decimal("100")))

    result = model.delivery_option_adjustment(contract, basket)
    scenario_ctds = {scenario.cheapest_to_deliver for scenario in result.scenarios}

    assert result.baseline_ctd == InstrumentId("long-duration")
    assert scenario_ctds == {InstrumentId("long-duration"), InstrumentId("short-duration")}
    assert result.delivery_option_adjustment > Decimal(0)


def test_fair_futures_price_and_oabpv_include_delivery_option_adjustment() -> None:
    contract, basket = _switching_contract_and_basket()
    model = YieldGridCTDSwitchModel((Decimal("-100"), Decimal("100")))

    with_option = fair_futures_price(contract, basket, delivery_option_model=model)
    without_option = fair_futures_price(contract, basket, delivery_option_model=NoDeliveryOptionModel())

    assert with_option.delivery_option_adjustment > Decimal(0)
    assert with_option.fair_futures_price < without_option.fair_futures_price
    assert oabpv(contract, basket, delivery_option_model=model) > Decimal(0)
