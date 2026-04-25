from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.inflation import (
    LinkerSwapParityCheck,
    breakeven_inflation_rate,
    linker_swap_parity_check,
    nominal_real_yield_basis,
    nominal_real_yield_spread,
)


def test_breakeven_inflation_rate_uses_exact_fisher_style_formula() -> None:
    result = breakeven_inflation_rate(
        nominal_yield=Decimal("0.05"),
        real_yield=Decimal("0.02"),
    )

    assert float(result) == pytest.approx(float(Decimal("1.05") / Decimal("1.02") - Decimal(1)), abs=1e-12)


def test_nominal_real_yield_basis_and_spread_match_simple_difference() -> None:
    basis = nominal_real_yield_basis(
        nominal_yield=Decimal("0.05"),
        real_yield=Decimal("0.02"),
    )

    assert basis == Decimal("0.03")
    assert nominal_real_yield_spread(
        nominal_yield=Decimal("0.05"),
        real_yield=Decimal("0.02"),
    ) == basis


def test_linker_swap_parity_check_reports_gap() -> None:
    implied = breakeven_inflation_rate(
        nominal_yield=Decimal("0.05"),
        real_yield=Decimal("0.02"),
    )
    result = linker_swap_parity_check(
        nominal_yield=Decimal("0.05"),
        real_yield=Decimal("0.02"),
        inflation_swap_rate=implied,
    )

    assert isinstance(result, LinkerSwapParityCheck)
    assert result.linker_breakeven == implied
    assert result.parity_gap == Decimal("0")
