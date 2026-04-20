from __future__ import annotations

from decimal import Decimal

from fuggers_py._measures.options import aggregate_option_greeks, option_rv_signal, scale_option_greeks, vega_notional
from fuggers_py._pricers.rates.options import black76_formula


def test_black76_delta_and_vega_match_finite_differences() -> None:
    forward = Decimal("0.035")
    strike = Decimal("0.03")
    volatility = Decimal("0.20")
    expiry_years = Decimal("2.0")
    forward_bump = Decimal("0.0001")
    volatility_bump = Decimal("0.0001")

    base = black76_formula(
        forward=forward,
        strike=strike,
        volatility=volatility,
        expiry_years=expiry_years,
        option_type="CALL",
    )
    up_forward = black76_formula(
        forward=forward + forward_bump,
        strike=strike,
        volatility=volatility,
        expiry_years=expiry_years,
        option_type="CALL",
    )
    down_forward = black76_formula(
        forward=forward - forward_bump,
        strike=strike,
        volatility=volatility,
        expiry_years=expiry_years,
        option_type="CALL",
    )
    up_vol = black76_formula(
        forward=forward,
        strike=strike,
        volatility=volatility + volatility_bump,
        expiry_years=expiry_years,
        option_type="CALL",
    )
    down_vol = black76_formula(
        forward=forward,
        strike=strike,
        volatility=volatility - volatility_bump,
        expiry_years=expiry_years,
        option_type="CALL",
    )

    fd_delta = (up_forward.present_value - down_forward.present_value) / (Decimal(2) * forward_bump)
    fd_vega = (up_vol.present_value - down_vol.present_value) / (Decimal(2) * volatility_bump)

    assert abs(base.greeks.delta - fd_delta) < Decimal("0.0005")
    assert abs(base.greeks.vega - fd_vega) < Decimal("0.0005")


def test_option_greeks_helpers_scale_aggregate_and_build_rv_signal() -> None:
    base = black76_formula(
        forward=Decimal("100"),
        strike=Decimal("100"),
        volatility=Decimal("0.25"),
        expiry_years=Decimal("1.0"),
        option_type="CALL",
    )
    scaled = scale_option_greeks(base.greeks, 2)
    total = aggregate_option_greeks([base.greeks, scaled])
    rv_signal = option_rv_signal(
        implied_volatility=Decimal("0.25"),
        realized_volatility=Decimal("0.21"),
        greeks=total,
    )

    assert total.delta == base.greeks.delta * Decimal(3)
    assert rv_signal.volatility_gap == Decimal("0.04")
    assert rv_signal.vega_notional == vega_notional(total)
