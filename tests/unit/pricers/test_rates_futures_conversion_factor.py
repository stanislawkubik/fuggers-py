from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.core import Date, Frequency
from fuggers_py.pricers.rates.futures import conversion_factor, theoretical_conversion_factor
from fuggers_py.products.rates.futures import DeliverableBond, GovernmentBondFuture


def test_theoretical_conversion_factor_matches_the_repo_bond_settlement_convention() -> None:
    contract = GovernmentBondFuture(
        delivery_date=Date.from_ymd(2026, 3, 1),
        standard_coupon_rate=Decimal("0.06"),
        coupon_frequency=Frequency.SEMI_ANNUAL,
    )
    deliverable = DeliverableBond(
        instrument_id="cf-par-bond",
        issue_date=Date.from_ymd(2024, 3, 1),
        maturity_date=Date.from_ymd(2034, 3, 1),
        coupon_rate="0.06",
        clean_price="100",
        frequency=Frequency.SEMI_ANNUAL,
    )

    assert float(theoretical_conversion_factor(contract, deliverable)) == pytest.approx(1.03, abs=1e-10)


def test_conversion_factor_prefers_published_override_when_present() -> None:
    contract = GovernmentBondFuture(
        delivery_date=Date.from_ymd(2026, 3, 1),
        standard_coupon_rate=Decimal("0.06"),
        coupon_frequency=Frequency.SEMI_ANNUAL,
    )
    deliverable = DeliverableBond(
        instrument_id="cf-published-bond",
        issue_date=Date.from_ymd(2024, 3, 1),
        maturity_date=Date.from_ymd(2036, 3, 1),
        coupon_rate="0.015",
        clean_price="80",
        frequency=Frequency.SEMI_ANNUAL,
        published_conversion_factor="0.8125",
    )

    theoretical = theoretical_conversion_factor(contract, deliverable)
    result = conversion_factor(contract, deliverable)

    assert theoretical != Decimal("0.8125")
    assert result.theoretical_conversion_factor == theoretical
    assert result.published_conversion_factor == Decimal("0.8125")
    assert result.conversion_factor == Decimal("0.8125")
    assert result.used_published_override is True
