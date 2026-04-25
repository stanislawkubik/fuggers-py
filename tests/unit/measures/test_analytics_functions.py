from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.bonds.analytics import (
    clean_price_from_yield,
    convexity,
    dv01,
    estimate_price_change,
    modified_duration,
    parse_day_count,
    price_change_from_duration,
    yield_to_maturity,
    yield_to_maturity_with_convention,
)
from fuggers_py.bonds.types import YieldConvention
from fuggers_py._core import Date, Price


def test_yield_price_roundtrip(fixed_rate_2025_bond) -> None:
    bond = fixed_rate_2025_bond
    settlement = Date.from_ymd(2020, 6, 15)
    price = Price.new(Decimal("105"), bond.currency())
    ytm = yield_to_maturity(bond, price, settlement)
    clean = clean_price_from_yield(bond, ytm, settlement)
    assert float(clean.as_percentage()) == pytest.approx(105.0, abs=1e-3)


def test_modified_duration_range(fixed_rate_2025_bond) -> None:
    bond = fixed_rate_2025_bond
    settlement = Date.from_ymd(2020, 6, 15)
    price = Price.new(Decimal("100"), bond.currency())
    ytm = yield_to_maturity(bond, price, settlement)
    md = modified_duration(bond, ytm, settlement)
    assert 3.5 <= float(md) <= 5.0


def test_convexity_range(fixed_rate_2025_bond) -> None:
    bond = fixed_rate_2025_bond
    settlement = Date.from_ymd(2020, 6, 15)
    price = Price.new(Decimal("100"), bond.currency())
    ytm = yield_to_maturity(bond, price, settlement)
    cx = convexity(bond, ytm, settlement)
    assert float(cx) > 0
    assert float(cx) < 200


def test_dv01_range(fixed_rate_2025_bond) -> None:
    bond = fixed_rate_2025_bond
    settlement = Date.from_ymd(2020, 6, 15)
    price = Price.new(Decimal("100"), bond.currency())
    ytm = yield_to_maturity(bond, price, settlement)
    val = dv01(bond, ytm, settlement)
    assert 0.03 <= float(val) <= 0.06


def test_estimate_price_change_negative() -> None:
    change = estimate_price_change(Decimal("5"), Decimal("50"), Decimal("100"), Decimal("0.01"))
    assert change < 0


def test_price_change_from_duration_matches_linear_approximation() -> None:
    change = price_change_from_duration(Decimal("5"), Decimal("100"), Decimal("0.01"))
    assert change == Decimal("-5.00")


def test_parse_day_count() -> None:
    assert parse_day_count("ACT/360").value == "ACT_360"
    assert parse_day_count("30/360").value == "THIRTY_360_US"
    assert parse_day_count("ACT/ACT ISDA").value == "ACT_ACT_ISDA"
    with pytest.raises(Exception):
        parse_day_count("UNKNOWN")


def test_yield_to_maturity_with_convention_dispatches_across_supported_conventions(fixed_rate_2025_bond) -> None:
    bond = fixed_rate_2025_bond
    settlement = Date.from_ymd(2020, 6, 15)
    price = Price.new(Decimal("105"), bond.currency())

    street = yield_to_maturity_with_convention(
        bond,
        price,
        settlement,
        YieldConvention.STREET_CONVENTION,
    )
    assert street == yield_to_maturity(bond, price, settlement)

    true_yield = yield_to_maturity_with_convention(
        bond,
        price,
        settlement,
        YieldConvention.TRUE_YIELD,
    )
    continuous = yield_to_maturity_with_convention(
        bond,
        price,
        settlement,
        YieldConvention.CONTINUOUS,
    )

    assert true_yield.value() > Decimal("0")
    assert continuous.value() > Decimal("0")
    assert continuous != street
