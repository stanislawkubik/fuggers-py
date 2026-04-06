"""In-memory portfolio storage adapters.

The store is deterministic: portfolios are keyed by id and as-of date, and
listing always follows a stable sorted order so snapshot-backed tests see
reproducible pagination.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fuggers_py.core.ids import PortfolioId
from fuggers_py.core.types import Date

from .storage import Page, Pagination, PortfolioFilter, PortfolioStore, StoredPortfolio


def _portfolio_sort_key(portfolio: StoredPortfolio) -> tuple[str, str, str]:
    """Return the stable sort key used for in-memory portfolio storage."""
    as_of = "" if portfolio.as_of is None else portfolio.as_of.as_naive_date().isoformat()
    name = "" if portfolio.name is None else portfolio.name
    return (portfolio.portfolio_id.as_str(), as_of, name)


@dataclass(slots=True)
class InMemoryPortfolioStore:
    """Deterministic in-memory portfolio store.

    The store keeps one record per portfolio id and as-of date. When no as-of
    date is supplied on lookup, the latest record according to the deterministic
    sort key is returned.
    """

    portfolios: dict[tuple[PortfolioId, Date | None], StoredPortfolio] = field(default_factory=dict)

    def __init__(self, portfolios: tuple[StoredPortfolio, ...] | list[StoredPortfolio] | None = None) -> None:
        self.portfolios = {}
        for portfolio in portfolios or ():
            self.upsert_portfolio(portfolio)

    def upsert_portfolio(self, portfolio: StoredPortfolio) -> StoredPortfolio:
        """Insert or replace a stored portfolio."""
        self.portfolios[(portfolio.portfolio_id, portfolio.as_of)] = portfolio
        return portfolio

    def get_portfolio(self, portfolio_id: PortfolioId | str, as_of: Date | None = None) -> StoredPortfolio | None:
        """Return the matching portfolio, preferring the latest as-of record."""
        resolved = PortfolioId.parse(portfolio_id)
        if as_of is not None:
            return self.portfolios.get((resolved, as_of))
        candidates = [portfolio for (candidate_id, _), portfolio in self.portfolios.items() if candidate_id == resolved]
        if not candidates:
            return None
        return max(candidates, key=_portfolio_sort_key)

    def list_portfolios(
        self,
        portfolio_filter: PortfolioFilter | None = None,
        pagination: Pagination | None = None,
    ) -> Page[StoredPortfolio]:
        """Return a paginated, deterministically ordered portfolio list."""
        pagination = pagination or Pagination()
        filtered = [
            portfolio
            for portfolio in sorted(self.portfolios.values(), key=_portfolio_sort_key)
            if portfolio_filter is None or portfolio_filter.matches(portfolio)
        ]
        return Page.from_sequence(filtered, pagination)

    def count_portfolios(self, portfolio_filter: PortfolioFilter | None = None) -> int:
        """Count portfolios that match the optional filter."""
        return sum(1 for portfolio in self.portfolios.values() if portfolio_filter is None or portfolio_filter.matches(portfolio))

    def delete_portfolio(self, portfolio_id: PortfolioId | str, as_of: Date | None = None) -> bool:
        """Delete a portfolio by id and optional as-of date."""
        resolved = PortfolioId.parse(portfolio_id)
        if as_of is not None:
            return self.portfolios.pop((resolved, as_of), None) is not None
        matching_keys = [key for key in self.portfolios if key[0] == resolved]
        for key in matching_keys:
            self.portfolios.pop(key, None)
        return bool(matching_keys)


__all__ = ["InMemoryPortfolioStore"]
