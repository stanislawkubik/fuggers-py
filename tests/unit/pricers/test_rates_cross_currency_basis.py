from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py._core import Currency, Date, Frequency, PayReceive
from fuggers_py._runtime.state import AnalyticsCurves
from fuggers_py._core import CurrencyPair
from fuggers_py.rates import CrossCurrencyBasisSwapPricer
from fuggers_py.rates import (
    CrossCurrencyBasisSwap,
    FloatingLegSpec,
    ScheduleDefinition,
)

from tests.helpers._rates_helpers import flat_curve, multicurve_analytics_curves, rate_index


class FlatFxForwardCurve:
    def __init__(self, *, pair: CurrencyPair, forward_rate: Decimal) -> None:
        self._pair = pair
        self._forward_rate = forward_rate

    def forward_rate(self, currency_pair: CurrencyPair | str, date: Date) -> Decimal:  # noqa: ARG002
        pair = currency_pair if isinstance(currency_pair, CurrencyPair) else CurrencyPair.parse(currency_pair)
        if pair == self._pair:
            return self._forward_rate
        if pair == CurrencyPair(base=self._pair.quote, quote=self._pair.base):
            return Decimal(1) / self._forward_rate
        raise KeyError(pair)


def _curves(
    reference_date: Date,
    *,
    usd_discount_rate: str,
    eur_discount_rate: str,
    usd_projection_rate: str,
    eur_projection_rate: str,
    fx_forward_curve: object | None = None,
) -> AnalyticsCurves:
    usd_discount_curve = flat_curve(reference_date, usd_discount_rate)
    eur_discount_curve = flat_curve(reference_date, eur_discount_rate)
    usd_projection_curve = flat_curve(reference_date, usd_projection_rate)
    eur_projection_curve = flat_curve(reference_date, eur_projection_rate)
    usd_index = rate_index("SOFR", "3M", Currency.USD)
    eur_index = rate_index("EURIBOR", "3M", Currency.EUR)
    return multicurve_analytics_curves(
        discount_curve=usd_discount_curve,
        discount_currency=Currency.USD,
        forward_curve=usd_projection_curve,
        additional_discount_curves={Currency.EUR: eur_discount_curve},
        fx_forward_curve=fx_forward_curve,
        projection_curves={usd_index: usd_projection_curve, eur_index: eur_projection_curve},
    )


def _swap(reference_date: Date, *, receive_spread: Decimal = Decimal(0)) -> CrossCurrencyBasisSwap:
    return CrossCurrencyBasisSwap(
        effective_date=reference_date,
        maturity_date=reference_date.add_years(3),
        pay_leg=FloatingLegSpec(
            pay_receive=PayReceive.PAY,
            notional=Decimal("1000000"),
            index_name="SOFR",
            index_tenor="3M",
            currency=Currency.USD,
            schedule=ScheduleDefinition(frequency=Frequency.QUARTERLY),
        ),
        receive_leg=FloatingLegSpec(
            pay_receive=PayReceive.RECEIVE,
            notional=Decimal("900000"),
            index_name="EURIBOR",
            index_tenor="3M",
            spread=receive_spread,
            currency=Currency.EUR,
            schedule=ScheduleDefinition(frequency=Frequency.QUARTERLY),
        ),
        spot_fx_rate=Decimal("0.90"),
        quoted_leg=PayReceive.RECEIVE,
    )


def test_cross_currency_basis_par_spread_is_zero_on_fx_hedged_identical_curves() -> None:
    reference_date = Date.from_ymd(2026, 1, 2)
    curves = _curves(
        reference_date,
        usd_discount_rate="0.03",
        eur_discount_rate="0.03",
        usd_projection_rate="0.03",
        eur_projection_rate="0.03",
    )

    result = CrossCurrencyBasisSwapPricer().price(_swap(reference_date), curves)

    assert float(result.par_spread) == pytest.approx(0.0, abs=1e-9)
    assert float(result.present_value) == pytest.approx(0.0, abs=1e-6)
    assert result.spread_annuity > Decimal(0)


def test_cross_currency_basis_par_spread_reprices_trade_with_explicit_fx_forward_curve() -> None:
    reference_date = Date.from_ymd(2026, 1, 2)
    fx_curve = FlatFxForwardCurve(
        pair=CurrencyPair(base=Currency.USD, quote=Currency.EUR),
        forward_rate=Decimal("0.95"),
    )
    curves = _curves(
        reference_date,
        usd_discount_rate="0.03",
        eur_discount_rate="0.03",
        usd_projection_rate="0.03",
        eur_projection_rate="0.03",
        fx_forward_curve=fx_curve,
    )
    pricer = CrossCurrencyBasisSwapPricer()
    swap = _swap(reference_date)
    result = pricer.price(swap, curves)
    par_swap = replace(swap, receive_leg=replace(swap.receive_leg, spread=result.par_spread))

    assert result.par_spread != Decimal(0)
    assert float(pricer.pv(par_swap, curves)) == pytest.approx(0.0, abs=1e-9)
