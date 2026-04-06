from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.measures.rv import (
    BondSignal,
    MaturitySignal,
    NeutralityTarget,
    SignalDirection,
    bond_pair_trade,
    bond_signal_workflow,
    maturity_pair_trade,
    maturity_signal_workflow,
    neutralize_bond_pair,
    neutralize_choices,
    select_bond_choice,
    select_bond_choices,
    select_maturity_choice,
    select_maturity_choices,
)

from tests.helpers._fitted_bond_helpers import exponential_model, fit_result


def _fit_result():
    return fit_result(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0.25"),
        mispricings={
            "UST4Y": Decimal("0.75"),
            "UST8Y": Decimal("-1.10"),
        },
    )


def test_maturity_signal_workflow_maps_factor_targets_into_filtered_bond_choices_and_a_neutral_trade() -> None:
    result = _fit_result()
    workflow = maturity_signal_workflow(
        result,
        signals=(
            MaturitySignal(name="belly_factor", target_maturity_years=Decimal("6.1"), score=Decimal("1.4")),
            MaturitySignal(name="front_factor", target_maturity_years=Decimal("4.0"), score=Decimal("-1.1")),
        ),
        benchmark_only=True,
        minimum_liquidity_score=Decimal("1.0"),
    )

    assert workflow.workflow_name == "maturity_signal_workflow"
    assert workflow.long_choice.direction is SignalDirection.LONG
    assert workflow.short_choice.direction is SignalDirection.SHORT
    assert workflow.long_choice.instrument_id.as_str() == "UST6Y"
    assert workflow.short_choice.instrument_id.as_str() == "UST4Y"
    assert workflow.trade.neutrality_target is NeutralityTarget.DV01
    assert float(workflow.trade.net_dv01) == pytest.approx(0.0, abs=1e-8)
    assert workflow.trade.expected_price_convergence > Decimal(0)


def test_bond_signal_workflow_uses_explicit_bond_signals_and_preserves_residual_signs() -> None:
    result = _fit_result()
    workflow = bond_signal_workflow(
        result,
        signals=(
            BondSignal(name="cheap_screen", instrument_id="UST8Y", score=Decimal("2.0")),
            BondSignal(name="rich_screen", instrument_id="UST4Y", score=Decimal("-1.8")),
        ),
    )

    assert workflow.long_choice.instrument_id.as_str() == "UST8Y"
    assert workflow.short_choice.instrument_id.as_str() == "UST4Y"
    assert workflow.trade.long_leg.bp_residual > Decimal(0)
    assert workflow.trade.short_leg.bp_residual < Decimal(0)
    assert workflow.trade.hedge_ratio > Decimal(0)
    assert workflow.trade.expected_bp_convergence > Decimal(0)


def test_selection_and_neutrality_leaf_helpers_are_usable_directly() -> None:
    result = _fit_result()
    long_signal = MaturitySignal(name="belly_factor", target_maturity_years=Decimal("6.1"), score=Decimal("1.4"))
    short_signal = BondSignal(name="rich_screen", instrument_id="UST4Y", score=Decimal("-1.8"))

    maturity_choice = select_maturity_choice(
        result,
        long_signal,
        benchmark_only=True,
        minimum_liquidity_score=Decimal("1.0"),
    )
    bond_choice = select_bond_choice(result, short_signal)
    maturity_choices = select_maturity_choices(result, signals=(long_signal,))
    bond_choices = select_bond_choices(result, signals=(short_signal,))
    trade = neutralize_choices(
        result,
        long_choice=maturity_choice,
        short_choice=bond_choice,
        neutrality_target=NeutralityTarget.DV01,
    )
    direct_trade = neutralize_bond_pair(
        result,
        long_instrument_id="UST8Y",
        short_instrument_id="UST4Y",
    )

    assert maturity_choice.instrument_id.as_str() == "UST6Y"
    assert bond_choice.instrument_id.as_str() == "UST4Y"
    assert maturity_choices[0] == maturity_choice
    assert bond_choices[0] == bond_choice
    assert float(trade.net_dv01) == pytest.approx(0.0, abs=1e-8)
    assert direct_trade.long_leg.instrument_id.as_str() == "UST8Y"
    assert direct_trade.short_leg.instrument_id.as_str() == "UST4Y"


def test_pair_trade_wrappers_delegate_to_the_workflow_surface() -> None:
    result = _fit_result()

    maturity_trade = maturity_pair_trade(
        result,
        long_signal=MaturitySignal(name="cheap_belly", target_maturity_years=Decimal("6.1"), score=Decimal("1.4")),
        short_signal=MaturitySignal(name="rich_front", target_maturity_years=Decimal("4.0"), score=Decimal("-1.1")),
    )
    bond_trade = bond_pair_trade(
        result,
        long_signal=BondSignal(name="cheap_screen", instrument_id="UST8Y", score=Decimal("2.0")),
        short_signal=BondSignal(name="rich_screen", instrument_id="UST4Y", score=Decimal("-1.8")),
    )

    assert maturity_trade.workflow_name == "maturity_signal_workflow"
    assert bond_trade.workflow_name == "bond_signal_workflow"
    assert bond_trade.trade.long_leg.instrument_id.as_str() == "UST8Y"


def test_maturity_signal_workflow_requires_both_a_long_and_a_short_signal() -> None:
    result = _fit_result()

    with pytest.raises(ValueError, match="LONG-directed signal"):
        maturity_signal_workflow(
            result,
            signals=(
                MaturitySignal(name="rich_front_end", target_maturity_years=Decimal("3.0"), score=Decimal("-0.5")),
                MaturitySignal(name="rich_belly", target_maturity_years=Decimal("5.0"), score=Decimal("-1.0")),
            ),
        )
