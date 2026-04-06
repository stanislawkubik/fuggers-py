"""Carry helpers for repo trades.

The helpers operate on repo-trade cash flows and return cash amounts or
dimensionless returns based on the repo cash lent by the trade.
"""

from __future__ import annotations

from decimal import Decimal

from fuggers_py.products.funding import RepoTrade


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def repo_financing_cost(trade: RepoTrade) -> Decimal:
    """Return the repo interest amount as a cash cost.

    Parameters
    ----------
    trade
        Repo trade to evaluate.

    Returns
    -------
    Decimal
        Cash interest amount over the repo term.
    """

    return trade.interest_amount()


def repo_net_carry(
    trade: RepoTrade,
    *,
    collateral_income: object = Decimal(0),
    haircut_financing_cost: object = Decimal(0),
) -> Decimal:
    """Return net repo carry after collateral income and haircut funding.

    Parameters
    ----------
    trade
        Repo trade to evaluate.
    collateral_income
        Cash income earned on the collateral position over the trade term.
    haircut_financing_cost
        Cash amount spent financing the haircut gap.

    Returns
    -------
    Decimal
        Net carry in currency units.
    """

    return _to_decimal(collateral_income) - trade.interest_amount() - _to_decimal(haircut_financing_cost)


def repo_carry_return(
    trade: RepoTrade,
    *,
    collateral_income: object = Decimal(0),
    haircut_financing_cost: object = Decimal(0),
) -> Decimal:
    """Return repo carry as a return on repo cash lent.

    The denominator is the repo cash advanced by the trade, not the
    collateral market value.
    """

    cash_lent = trade.cash_lent()
    if cash_lent == Decimal(0):
        raise ValueError("repo_carry_return requires non-zero cash lent.")
    return repo_net_carry(
        trade,
        collateral_income=collateral_income,
        haircut_financing_cost=haircut_financing_cost,
    ) / cash_lent


__all__ = [
    "repo_carry_return",
    "repo_financing_cost",
    "repo_net_carry",
]
