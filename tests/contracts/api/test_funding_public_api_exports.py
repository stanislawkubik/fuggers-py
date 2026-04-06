from __future__ import annotations

from fuggers_py.market.quotes import HaircutQuote as data_haircut_quote
from fuggers_py.market.quotes import RepoQuote as data_repo_quote
from fuggers_py.reference import RepoReferenceData as data_repo_reference_data
from fuggers_py.market.quotes import HaircutQuote, RepoQuote
from fuggers_py.market.curves.funding import RepoCurve
from fuggers_py.measures.funding import (
    all_in_financing_cost,
    financed_cash,
    futures_invoice_amount,
    haircut_amount,
    haircut_drag,
    haircut_financing_cost,
    implied_repo_rate,
    implied_repo_rate_from_trade,
    is_special,
    repo_carry_return,
    repo_financing_cost,
    repo_net_carry,
    specialness_spread,
    specialness_value,
)
from fuggers_py.products.funding import RepoTrade
from fuggers_py.reference import RepoReferenceData
from fuggers_py.measures.funding import all_in_financing_cost as analytics_all_in_financing_cost
from fuggers_py.measures.funding import financed_cash as analytics_financed_cash
from fuggers_py.measures.funding import futures_invoice_amount as analytics_futures_invoice_amount
from fuggers_py.measures.funding import haircut_amount as analytics_haircut_amount
from fuggers_py.measures.funding import haircut_drag as analytics_haircut_drag
from fuggers_py.measures.funding import haircut_financing_cost as analytics_haircut_financing_cost
from fuggers_py.measures.funding import implied_repo_rate as analytics_implied_repo_rate
from fuggers_py.measures.funding import implied_repo_rate_from_trade as analytics_implied_repo_rate_from_trade
from fuggers_py.measures.funding import is_special as analytics_is_special
from fuggers_py.measures.funding import repo_carry_return as analytics_repo_carry_return
from fuggers_py.measures.funding import repo_financing_cost as analytics_repo_financing_cost
from fuggers_py.measures.funding import repo_net_carry as analytics_repo_net_carry
from fuggers_py.measures.funding import specialness_spread as analytics_specialness_spread
from fuggers_py.measures.funding import specialness_value as analytics_specialness_value
from fuggers_py.market.curves.funding import RepoCurve as curves_repo_curve
from fuggers_py.products.funding import RepoTrade as instruments_repo_trade


def test_funding_root_exports_scaffold_records() -> None:
    assert RepoQuote is data_repo_quote
    assert HaircutQuote is data_haircut_quote
    assert RepoReferenceData is data_repo_reference_data
    assert RepoTrade is instruments_repo_trade
    assert RepoCurve is curves_repo_curve
    assert financed_cash is analytics_financed_cash
    assert haircut_amount is analytics_haircut_amount
    assert haircut_drag is analytics_haircut_drag
    assert implied_repo_rate is analytics_implied_repo_rate
    assert implied_repo_rate_from_trade is analytics_implied_repo_rate_from_trade
    assert repo_financing_cost is analytics_repo_financing_cost
    assert repo_carry_return is analytics_repo_carry_return
    assert repo_net_carry is analytics_repo_net_carry
    assert is_special is analytics_is_special
    assert specialness_spread is analytics_specialness_spread
    assert specialness_value is analytics_specialness_value
    assert futures_invoice_amount is analytics_futures_invoice_amount
    assert haircut_financing_cost is analytics_haircut_financing_cost
    assert all_in_financing_cost is analytics_all_in_financing_cost
