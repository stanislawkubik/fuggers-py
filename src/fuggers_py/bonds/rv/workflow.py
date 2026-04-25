"""Workflow hooks from external signals into deterministic RV trades."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ._fit_result import FittedBondResult
from .neutrality import NeutralityTarget, NeutralizedTradeExpression, neutralize_choices
from .selection import (
    BondChoice,
    BondSignal,
    MaturityChoice,
    MaturitySignal,
    SignalDirection,
    select_bond_choice,
    select_maturity_choice,
)


def _pick_long_signal(signals):
    long_candidates = [signal for signal in signals if signal.resolved_direction() is SignalDirection.LONG]
    if not long_candidates:
        raise ValueError("The workflow requires at least one LONG-directed signal.")
    return max(long_candidates, key=lambda signal: (abs(signal.score), signal.name))


def _pick_short_signal(signals):
    short_candidates = [signal for signal in signals if signal.resolved_direction() is SignalDirection.SHORT]
    if not short_candidates:
        raise ValueError("The workflow requires at least one SHORT-directed signal.")
    return max(short_candidates, key=lambda signal: (abs(signal.score), signal.name))


@dataclass(frozen=True, slots=True)
class RvWorkflowResult:
    """Selected RV trade and the signals that produced it."""

    workflow_name: str
    long_choice: MaturityChoice | BondChoice
    short_choice: MaturityChoice | BondChoice
    trade: NeutralizedTradeExpression

    def __post_init__(self) -> None:
        object.__setattr__(self, "workflow_name", self.workflow_name.strip())


def maturity_signal_workflow(
    fit_result: FittedBondResult,
    signals: tuple[MaturitySignal, ...],
    *,
    base_long_notional: object = Decimal("1000000"),
    neutrality_target: NeutralityTarget | str = NeutralityTarget.DV01,
    benchmark_only: bool = False,
    minimum_liquidity_score: object | None = None,
) -> RvWorkflowResult:
    """Build a maturity-based RV workflow result from a signal list."""
    if len(signals) < 2:
        raise ValueError("maturity_signal_workflow requires at least two maturity signals.")
    long_signal = _pick_long_signal(signals)
    short_signal = _pick_short_signal(signals)
    long_choice = select_maturity_choice(
        fit_result,
        long_signal,
        benchmark_only=benchmark_only,
        minimum_liquidity_score=minimum_liquidity_score,
    )
    short_choice = select_maturity_choice(
        fit_result,
        short_signal,
        benchmark_only=benchmark_only,
        minimum_liquidity_score=minimum_liquidity_score,
    )
    trade = neutralize_choices(
        fit_result,
        long_choice=long_choice,
        short_choice=short_choice,
        base_long_notional=base_long_notional,
        neutrality_target=neutrality_target,
    )
    return RvWorkflowResult(
        workflow_name="maturity_signal_workflow",
        long_choice=long_choice,
        short_choice=short_choice,
        trade=trade,
    )


def bond_signal_workflow(
    fit_result: FittedBondResult,
    signals: tuple[BondSignal, ...],
    *,
    base_long_notional: object = Decimal("1000000"),
    neutrality_target: NeutralityTarget | str = NeutralityTarget.DV01,
) -> RvWorkflowResult:
    """Build a bond-specific RV workflow result from a signal list."""
    if len(signals) < 2:
        raise ValueError("bond_signal_workflow requires at least two bond signals.")
    long_signal = _pick_long_signal(signals)
    short_signal = _pick_short_signal(signals)
    long_choice = select_bond_choice(fit_result, long_signal)
    short_choice = select_bond_choice(fit_result, short_signal)
    trade = neutralize_choices(
        fit_result,
        long_choice=long_choice,
        short_choice=short_choice,
        base_long_notional=base_long_notional,
        neutrality_target=neutrality_target,
    )
    return RvWorkflowResult(
        workflow_name="bond_signal_workflow",
        long_choice=long_choice,
        short_choice=short_choice,
        trade=trade,
    )


__all__ = [
    "RvWorkflowResult",
    "bond_signal_workflow",
    "maturity_signal_workflow",
]
