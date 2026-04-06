from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.core import Currency, Date, Frequency
from fuggers_py.products.credit import CreditDefaultSwap
from fuggers_py.products.instruments import (
    HasExpiry,
    HasOptionType,
    HasUnderlyingInstrument,
    Instrument,
)
from fuggers_py.products.rates import (
    BasisSwap,
    CapFloor,
    CrossCurrencyBasisSwap,
    FixedFloatSwap,
    FixedLegSpec,
    FloatingLegSpec,
    Fra,
    GovernmentBondFuture,
    Ois,
    PayReceive,
    ScheduleDefinition,
    StandardCouponInflationSwap,
    Swaption,
    ZeroCouponInflationSwap,
)
from fuggers_py.products.rates.options import CapFloorType, FuturesOption, OptionType


def _fixed_leg(
    pay_receive: PayReceive,
    *,
    currency: Currency = Currency.USD,
    fixed_rate: str = "0.03",
) -> FixedLegSpec:
    return FixedLegSpec(
        pay_receive=pay_receive,
        notional=Decimal("1000000"),
        fixed_rate=Decimal(fixed_rate),
        currency=currency,
        schedule=ScheduleDefinition(frequency=Frequency.SEMI_ANNUAL),
    )


def _floating_leg(
    pay_receive: PayReceive,
    *,
    currency: Currency = Currency.USD,
    index_name: str = "SOFR",
    index_tenor: str = "3M",
    spread: str = "0.0",
    frequency: Frequency = Frequency.QUARTERLY,
) -> FloatingLegSpec:
    return FloatingLegSpec(
        pay_receive=pay_receive,
        notional=Decimal("1000000"),
        index_name=index_name,
        index_tenor=index_tenor,
        spread=Decimal(spread),
        currency=currency,
        schedule=ScheduleDefinition(frequency=frequency),
    )


def _fixed_float_swap() -> FixedFloatSwap:
    return FixedFloatSwap(
        effective_date=Date.from_ymd(2026, 1, 2),
        maturity_date=Date.from_ymd(2031, 1, 2),
        fixed_leg=_fixed_leg(PayReceive.PAY),
        floating_leg=_floating_leg(PayReceive.RECEIVE),
        instrument_id="SWAP-1",
    )


def _ois() -> Ois:
    return Ois(
        effective_date=Date.from_ymd(2026, 1, 2),
        maturity_date=Date.from_ymd(2029, 1, 2),
        fixed_leg=_fixed_leg(PayReceive.RECEIVE),
        floating_leg=_floating_leg(PayReceive.PAY, index_tenor="1M"),
        instrument_id="OIS-1",
    )


def _fra() -> Fra:
    return Fra(
        start_date=Date.from_ymd(2026, 4, 2),
        end_date=Date.from_ymd(2026, 7, 2),
        notional=Decimal("1000000"),
        fixed_rate=Decimal("0.031"),
        pay_receive=PayReceive.RECEIVE,
        currency=Currency.USD,
        index_name="SOFR",
        index_tenor="3M",
        instrument_id="FRA-1",
    )


def _basis_swap() -> BasisSwap:
    return BasisSwap(
        effective_date=Date.from_ymd(2026, 1, 2),
        maturity_date=Date.from_ymd(2029, 1, 2),
        pay_leg=_floating_leg(PayReceive.PAY, index_name="SOFR", index_tenor="3M"),
        receive_leg=_floating_leg(
            PayReceive.RECEIVE,
            index_name="TERM",
            index_tenor="6M",
            frequency=Frequency.SEMI_ANNUAL,
        ),
        quoted_leg=PayReceive.RECEIVE,
        instrument_id="BASIS-1",
    )


def _cross_currency_basis_swap() -> CrossCurrencyBasisSwap:
    return CrossCurrencyBasisSwap(
        effective_date=Date.from_ymd(2026, 1, 2),
        maturity_date=Date.from_ymd(2029, 1, 2),
        pay_leg=_floating_leg(PayReceive.PAY, currency=Currency.USD, index_name="SOFR", index_tenor="3M"),
        receive_leg=_floating_leg(
            PayReceive.RECEIVE,
            currency=Currency.EUR,
            index_name="EURIBOR",
            index_tenor="3M",
        ),
        spot_fx_rate=Decimal("0.92"),
        quoted_leg=PayReceive.RECEIVE,
        instrument_id="XCCY-1",
    )


def _zero_coupon_inflation_swap() -> ZeroCouponInflationSwap:
    return ZeroCouponInflationSwap.new(
        trade_date=Date.from_ymd(2024, 1, 10),
        effective_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2025, 1, 15),
        notional=Decimal("1000000"),
        fixed_rate=Decimal("0.02"),
        pay_receive=PayReceive.PAY,
        currency=Currency.USD,
        instrument_id="ZCIS-1",
    )


def _standard_coupon_inflation_swap() -> StandardCouponInflationSwap:
    return StandardCouponInflationSwap.new(
        trade_date=Date.from_ymd(2024, 1, 10),
        effective_date=Date.from_ymd(2024, 1, 2),
        maturity_date=Date.from_ymd(2025, 1, 2),
        notional=Decimal("1000000"),
        fixed_rate=Decimal("0.02"),
        pay_receive=PayReceive.PAY,
        currency=Currency.USD,
        schedule=ScheduleDefinition(frequency=Frequency.SEMI_ANNUAL),
        normalize_effective_date_to_reference_month_start=False,
        instrument_id="SCIS-1",
    )


def _government_bond_future() -> GovernmentBondFuture:
    return GovernmentBondFuture(
        delivery_date=Date.from_ymd(2026, 3, 15),
        currency=Currency.USD,
        instrument_id="TYH6",
    )


def _swaption() -> Swaption:
    return Swaption(
        expiry_date=Date.from_ymd(2026, 7, 15),
        underlying_swap=FixedFloatSwap(
            effective_date=Date.from_ymd(2026, 7, 15),
            maturity_date=Date.from_ymd(2031, 7, 15),
            fixed_leg=_fixed_leg(PayReceive.PAY),
            floating_leg=_floating_leg(PayReceive.RECEIVE),
            instrument_id="SWAPTION-SWAP-1",
        ),
        strike=Decimal("0.035"),
        exercise_into=PayReceive.PAY,
        instrument_id="SWOPT-1",
    )


def _futures_option() -> FuturesOption:
    return FuturesOption(
        expiry_date=Date.from_ymd(2026, 2, 15),
        underlying_future=_government_bond_future(),
        strike=Decimal("110"),
        option_type=OptionType.CALL,
        instrument_id="FUTOPT-1",
    )


def _cap_floor() -> CapFloor:
    return CapFloor(
        effective_date=Date.from_ymd(2026, 1, 15),
        maturity_date=Date.from_ymd(2026, 10, 15),
        floating_leg=_floating_leg(PayReceive.RECEIVE),
        strike=Decimal("0.03"),
        cap_floor_type=CapFloorType.CAP,
        instrument_id="CAP-1",
    )


def _credit_default_swap() -> CreditDefaultSwap:
    return CreditDefaultSwap(
        effective_date=Date.from_ymd(2026, 1, 2),
        maturity_date=Date.from_ymd(2031, 1, 2),
        running_spread=Decimal("0.012"),
        notional=Decimal("1000000"),
        instrument_id="CDS-1",
    )


@pytest.mark.feature_slug("non-bond-instrument-adoption")
@pytest.mark.feature_category("unit")
@pytest.mark.parametrize(
    ("builder", "expected_kind"),
    [
        pytest.param(_credit_default_swap, "credit.cds", id="CreditDefaultSwap"),
        pytest.param(_fixed_float_swap, "rates.swap.fixed_float", id="FixedFloatSwap"),
        pytest.param(_ois, "rates.swap.ois", id="Ois"),
        pytest.param(_fra, "rates.fra", id="Fra"),
        pytest.param(_basis_swap, "rates.swap.basis", id="BasisSwap"),
        pytest.param(
            _cross_currency_basis_swap,
            "rates.swap.cross_currency_basis",
            id="CrossCurrencyBasisSwap",
        ),
        pytest.param(
            _zero_coupon_inflation_swap,
            "rates.swap.inflation.zero_coupon",
            id="ZeroCouponInflationSwap",
        ),
        pytest.param(
            _standard_coupon_inflation_swap,
            "rates.swap.inflation.standard_coupon",
            id="StandardCouponInflationSwap",
        ),
        pytest.param(
            _government_bond_future,
            "rates.future.government_bond",
            id="GovernmentBondFuture",
        ),
        pytest.param(_swaption, "rates.option.swaption", id="Swaption"),
        pytest.param(_futures_option, "rates.option.futures", id="FuturesOption"),
        pytest.param(_cap_floor, "rates.option.cap_floor", id="CapFloor"),
    ],
)
def test_listed_contracts_expose_exact_kind_and_conform_to_instrument(builder, expected_kind: str) -> None:
    instrument = builder()

    assert type(instrument).KIND == expected_kind
    assert instrument.kind == expected_kind
    assert isinstance(instrument, Instrument)


@pytest.mark.feature_slug("non-bond-instrument-adoption")
@pytest.mark.feature_category("unit")
def test_option_wrappers_expose_only_the_requested_structural_capabilities() -> None:
    swaption = _swaption()
    futures_option = _futures_option()
    cap_floor = _cap_floor()

    assert isinstance(swaption, HasExpiry)
    assert isinstance(swaption, HasUnderlyingInstrument)
    assert swaption.underlying is swaption.underlying_swap

    assert isinstance(futures_option, HasExpiry)
    assert isinstance(futures_option, HasUnderlyingInstrument)
    assert futures_option.underlying is futures_option.underlying_future

    assert isinstance(cap_floor, HasOptionType)
    assert cap_floor.option_type() is OptionType.CALL
    assert not isinstance(cap_floor, HasUnderlyingInstrument)
    assert not hasattr(cap_floor, "underlying")
