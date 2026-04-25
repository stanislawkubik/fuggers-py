from __future__ import annotations

import sys
from pathlib import Path

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addini(
        "asyncio_default_fixture_loop_scope",
        "Compatibility shim for environments without pytest-asyncio.",
        default="function",
    )


def pytest_configure(config: pytest.Config) -> None:
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    sys.path.insert(0, str(src))
    config.addinivalue_line(
        "markers",
        "validation: deterministic validation harness that cross-checks public analytics against curated references",
    )
    config.addinivalue_line(
        "markers",
        "asyncio: run the marked test in an event loop via pytest-asyncio",
    )


@pytest.fixture()
def fixed_rate_2025_bond():
    from decimal import Decimal

    from fuggers_py import Currency, Date, Frequency
    from fuggers_py.bonds.instruments import FixedBondBuilder
    from fuggers_py._core import YieldCalculationRules

    issue = Date.from_ymd(2015, 6, 15)
    maturity = Date.from_ymd(2025, 6, 15)

    bond = (
        FixedBondBuilder.new()
        .with_issue_date(issue)
        .with_maturity_date(maturity)
        .with_coupon_rate(Decimal("0.075"))
        .with_frequency(Frequency.SEMI_ANNUAL)
        .with_currency(Currency.USD)
        .with_rules(YieldCalculationRules.us_corporate())
        .build()
    )
    return bond
