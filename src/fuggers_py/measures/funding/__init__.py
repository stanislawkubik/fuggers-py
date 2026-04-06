"""Funding desk analytics and carry measures.

This package covers repo carry, haircut financing, implied repo, and repo
specialness helpers. Cash amounts are returned in currency units and rates are
returned as raw decimals unless a helper explicitly says otherwise.
"""

from __future__ import annotations

from .carry import repo_carry_return, repo_financing_cost, repo_net_carry
from .haircuts import all_in_financing_cost, financed_cash, haircut_amount, haircut_drag, haircut_financing_cost
from .implied_repo import futures_invoice_amount, implied_repo_rate, implied_repo_rate_from_trade
from .specialness import is_special, specialness_spread, specialness_value

__all__ = [
    "all_in_financing_cost",
    "financed_cash",
    "futures_invoice_amount",
    "haircut_amount",
    "haircut_drag",
    "haircut_financing_cost",
    "implied_repo_rate",
    "implied_repo_rate_from_trade",
    "is_special",
    "repo_carry_return",
    "repo_financing_cost",
    "repo_net_carry",
    "specialness_spread",
    "specialness_value",
]
