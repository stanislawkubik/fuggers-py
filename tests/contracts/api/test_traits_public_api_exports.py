from __future__ import annotations

from decimal import Decimal

from fuggers_py.core import Date
from fuggers_py.reference import Tenor as bonds_tenor
from fuggers_py.core import PortfolioId
from fuggers_py.adapters import PortfolioFilter, PortfolioStore, StoredPortfolio, StoredPosition
from fuggers_py.reference import Tenor


def test_traits_root_reexports_tenor() -> None:
    assert Tenor is bonds_tenor
    assert str(Tenor.parse("5Y")) == "5Y"


def test_traits_root_reexports_storage_records() -> None:
    portfolio = StoredPortfolio(
        portfolio_id=PortfolioId("fixture-portfolio"),
        positions=(StoredPosition("US1234567890", quantity=Decimal("100")),),
        as_of=Date.from_ymd(2026, 3, 13),
    )

    assert portfolio.position_count == 1
    assert isinstance(PortfolioFilter(), PortfolioFilter)
    assert PortfolioStore.__name__ == "PortfolioStore"
