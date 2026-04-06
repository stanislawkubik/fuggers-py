from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from fuggers_py.core import Date
from fuggers_py.core import InstrumentId
from fuggers_py.pricers.rates.futures import (
    MultiFactorDeliveryOptionModel,
    MultiFactorScenario,
    NoDeliveryOptionModel,
    OneFactorDeliveryOptionModel,
    fair_futures_price,
)
from fuggers_py.products.rates.futures import (
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


def test_one_factor_delivery_option_model_adds_probability_weighted_adjustment() -> None:
    contract, basket = _switching_contract_and_basket()
    model = OneFactorDeliveryOptionModel(
        yield_volatility_bps=Decimal("100"),
        scenario_multipliers=(Decimal("-1"), Decimal("1")),
        scenario_probabilities=(Decimal("0.4"), Decimal("0.6")),
    )

    result = model.delivery_option_adjustment(contract, basket)

    assert result.delivery_option_adjustment > Decimal(0)
    assert sum((scenario.probability for scenario in result.scenarios if scenario.probability is not None), start=Decimal(0)) == Decimal(1)
    assert {scenario.cheapest_to_deliver for scenario in result.scenarios} == {
        InstrumentId("long-duration"),
        InstrumentId("short-duration"),
    }


def test_multi_factor_delivery_option_model_preserves_fair_price_interface() -> None:
    contract, basket = _switching_contract_and_basket()
    model = MultiFactorDeliveryOptionModel(
        factor_volatilities_bps=(Decimal("80"),),
        deliverable_factor_loadings={
            InstrumentId("long-duration"): (Decimal("1.5"),),
            InstrumentId("short-duration"): (Decimal("0.5"),),
        },
        scenarios=(
            MultiFactorScenario((Decimal("-1"),), probability=Decimal("0.5"), label="bull"),
            MultiFactorScenario((Decimal("1"),), probability=Decimal("0.5"), label="bear"),
        ),
    )

    with_option = fair_futures_price(contract, basket, delivery_option_model=model)
    without_option = fair_futures_price(contract, basket, delivery_option_model=NoDeliveryOptionModel())

    assert with_option.delivery_option_adjustment > Decimal(0)
    assert with_option.fair_futures_price < without_option.fair_futures_price
