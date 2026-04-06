from __future__ import annotations

from decimal import Decimal

from fuggers_py.pricers.rates.futures import basis_metrics, gross_basis, net_basis


def test_basis_helpers_follow_the_documented_sign_convention() -> None:
    gross = gross_basis("111.50", "0.80", "90.10")
    net = net_basis(
        "111.50",
        "0.80",
        "90.10",
        financing_cost="0.35",
        coupon_income="0.10",
        delivery_option_value="0.05",
    )
    metrics = basis_metrics(
        "111.50",
        "0.80",
        "90.10",
        financing_cost="0.35",
        coupon_income="0.10",
        delivery_option_value="0.05",
    )

    assert gross == Decimal("0.9000")
    assert net == Decimal("1.1000")
    assert metrics.gross_basis == Decimal("0.9000")
    assert metrics.net_basis == Decimal("1.1000")
    assert metrics.delivery_payoff == Decimal("-0.9000")
