from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.bonds.risk import aggregate_portfolio_risk, duration_hedge_ratio, dv01_hedge_ratio, historical_var, parametric_var
from fuggers_py.bonds.risk import Position
from fuggers_py.bonds.risk import parametric_var_from_dv01
from fuggers_py.bonds import InvalidInput


def test_parametric_var_uses_left_tail_and_non_negative_floor() -> None:
    result = parametric_var([0.01, 0.01, 0.01], confidence=0.95)
    assert result.value == Decimal("0.0")


def test_historical_var_interpolates_tail_quantile() -> None:
    result = historical_var([-0.03, -0.01, 0.01, 0.02], confidence=0.75)
    assert float(result.value) == pytest.approx(0.015, abs=1e-12)


def test_var_helpers_validate_confidence() -> None:
    with pytest.raises(InvalidInput):
        parametric_var([0.01, -0.01], confidence=1.0)

    with pytest.raises(InvalidInput):
        historical_var([0.01, -0.01], confidence=0.0)


def test_parametric_var_from_dv01_uses_risk_magnitude() -> None:
    result = parametric_var_from_dv01(Decimal("-12.5"), shock_bps=-25.0, confidence=0.95)
    assert result.value > 0


def test_duration_and_dv01_hedge_ratio_behave_consistently() -> None:
    assert duration_hedge_ratio(5, 100, 5, 100) == Decimal(1)
    assert dv01_hedge_ratio(Decimal("12.5"), Decimal("2.5")) == Decimal("5")

    with pytest.raises(ValueError):
        duration_hedge_ratio(5, 0, 5, 100)


def test_aggregate_portfolio_risk_uses_market_value_weighting() -> None:
    positions = [
        Position(modified_duration=Decimal("10"), dirty_price=Decimal("50"), face=Decimal("100")),
        Position(modified_duration=Decimal("0"), dirty_price=Decimal("150"), face=Decimal("100")),
    ]

    risk = aggregate_portfolio_risk(positions)

    assert float(risk.weighted_duration) == pytest.approx(2.5, abs=1e-12)
    assert risk.dv01 > 0
