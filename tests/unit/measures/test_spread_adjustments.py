from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.bonds.spreads import (
    BalanceSheetSpreadOverlay,
    CapitalSpreadAdjustment,
    HaircutSpreadAdjustment,
    ShadowCostSpreadAdjustment,
    apply_balance_sheet_overlays,
    capital_adjustment_breakdown,
    haircut_adjustment_breakdown,
    shadow_cost_adjustment_breakdown,
    utilization_ratio,
)


def test_haircut_adjustment_breakdown_reports_drag_amount_and_spread() -> None:
    breakdown = haircut_adjustment_breakdown(
        collateral_value=Decimal("100"),
        haircut=Decimal("0.02"),
        repo_rate=Decimal("0.0300"),
        haircut_funding_rate=Decimal("0.0500"),
        year_fraction=Decimal("0.25"),
    )

    assert breakdown.haircut_amount == Decimal("2.00")
    assert breakdown.drag_amount == Decimal("0.010000")
    assert breakdown.spread_adjustment == Decimal("0.0004")


def test_capital_adjustment_breakdown_translates_capital_charge_into_spread() -> None:
    breakdown = capital_adjustment_breakdown(
        exposure=Decimal("100"),
        risk_weight=Decimal("0.50"),
        capital_ratio=Decimal("0.10"),
        hurdle_rate=Decimal("0.12"),
        pass_through=Decimal("0.75"),
    )

    assert breakdown.capital_consumed == Decimal("5.0000")
    assert breakdown.annual_capital_cost == Decimal("0.600000")
    assert breakdown.passed_through_cost == Decimal("0.45000000")
    assert breakdown.spread_adjustment == Decimal("0.00450000")


def test_shadow_cost_adjustment_supports_usage_capacity_utilization() -> None:
    breakdown = shadow_cost_adjustment_breakdown(
        shadow_cost_rate=Decimal("0.0020"),
        usage=Decimal("75"),
        capacity=Decimal("100"),
        pass_through=Decimal("0.50"),
    )

    assert utilization_ratio(usage=Decimal("75"), capacity=Decimal("100")) == Decimal("0.75")
    assert breakdown.utilization == Decimal("0.75")
    assert breakdown.spread_adjustment == Decimal("0.000750")


def test_balance_sheet_overlay_adds_components_and_preserves_credit_split() -> None:
    overlay = BalanceSheetSpreadOverlay(
        adjustments=(
            HaircutSpreadAdjustment(
                collateral_value=Decimal("100"),
                haircut=Decimal("0.02"),
                repo_rate=Decimal("0.0300"),
                haircut_funding_rate=Decimal("0.0500"),
                year_fraction=Decimal("0.25"),
            ),
            CapitalSpreadAdjustment(
                exposure=Decimal("100"),
                risk_weight=Decimal("0.50"),
                capital_ratio=Decimal("0.10"),
                hurdle_rate=Decimal("0.12"),
                pass_through=Decimal("0.75"),
            ),
            ShadowCostSpreadAdjustment(
                shadow_cost_rate=Decimal("0.0020"),
                usage=Decimal("75"),
                capacity=Decimal("100"),
                pass_through=Decimal("0.50"),
            ),
        )
    )

    summary = overlay.apply(base_spread=Decimal("0.0100"))
    funding_result = overlay.apply_to_funding_spread(
        base_funding_spread=Decimal("0.0060"),
        credit_spread=Decimal("0.0040"),
    )

    assert len(summary.components) == 3
    assert summary.total_adjustment == Decimal("0.00565000")
    assert summary.adjusted_spread == Decimal("0.01565000")
    assert funding_result.adjusted_funding_spread == Decimal("0.01165000")
    assert funding_result.adjusted_all_in_spread == Decimal("0.01565000")
    assert apply_balance_sheet_overlays(
        base_spread=Decimal("0.0100"),
        adjustments=overlay.adjustments,
    ) == summary


def test_haircut_adjustment_validates_inputs() -> None:
    with pytest.raises(ValueError, match="haircut between 0 and 1"):
        haircut_adjustment_breakdown(
            collateral_value=Decimal("100"),
            haircut=Decimal("1.20"),
            repo_rate=Decimal("0.03"),
            haircut_funding_rate=Decimal("0.05"),
        )

