from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._core import Currency, Date
from fuggers_py._storage import (
    InMemoryPortfolioStore,
    JsonCodec,
    PortfolioFilter,
    SQLiteStorageAdapter,
    StoredPortfolio,
    StoredPosition,
)
from fuggers_py._core import PortfolioId
from fuggers_py._storage import Pagination, PortfolioStore


def _portfolio(
    portfolio_id: str,
    *,
    as_of: Date | None,
    source: str,
    positions: tuple[StoredPosition, ...],
    name: str,
) -> StoredPortfolio:
    return StoredPortfolio(
        portfolio_id=PortfolioId(portfolio_id),
        positions=positions,
        as_of=as_of,
        currency=Currency.USD,
        name=name,
        source=source,
    )


def test_in_memory_portfolio_store_is_deterministic_and_filterable() -> None:
    alpha_old = _portfolio(
        "alpha",
        as_of=Date.from_ymd(2026, 3, 13),
        source="research",
        name="Alpha Core",
        positions=(
            StoredPosition("US1234567890", quantity=Decimal("100"), label="core"),
            StoredPosition("US0987654321", weight=Decimal("0.35")),
        ),
    )
    alpha_new = _portfolio(
        "alpha",
        as_of=Date.from_ymd(2026, 3, 14),
        source="research",
        name="Alpha Core",
        positions=(
            StoredPosition("US1234567890", quantity=Decimal("120"), label="core"),
            StoredPosition("US1111111111", weight=Decimal("0.20")),
        ),
    )
    beta = _portfolio(
        "beta",
        as_of=Date.from_ymd(2026, 3, 13),
        source="ops",
        name="Beta Income",
        positions=(StoredPosition("US2222222222", quantity=Decimal("80")),),
    )
    store = InMemoryPortfolioStore([beta, alpha_new, alpha_old])

    assert isinstance(store, PortfolioStore)
    assert store.get_portfolio("alpha") == alpha_new
    assert store.get_portfolio("alpha", Date.from_ymd(2026, 3, 13)) == alpha_old
    assert store.get_portfolio("missing") is None

    first_page = store.list_portfolios(pagination=Pagination(limit=2))
    second_page = store.list_portfolios(pagination=Pagination(limit=2, cursor=first_page.next_cursor))

    assert first_page.total_items == 3
    assert [item.portfolio_id.as_str() for item in first_page.items] == ["alpha", "alpha"]
    assert second_page.items == (beta,)

    filtered = store.list_portfolios(
        PortfolioFilter(
            source="research",
            instrument_id="US1234567890",
            name_contains="alpha",
        )
    )
    assert filtered.items == (alpha_old, alpha_new)
    assert store.count_portfolios(PortfolioFilter(source="research")) == 2

    assert store.delete_portfolio("alpha", Date.from_ymd(2026, 3, 13)) is True
    assert store.get_portfolio("alpha", Date.from_ymd(2026, 3, 13)) is None
    assert store.delete_portfolio("alpha") is True
    assert store.get_portfolio("alpha") is None


def test_stored_portfolio_round_trips_through_json_codec_and_sqlite_codec() -> None:
    portfolio = _portfolio(
        "round-trip",
        as_of=Date.from_ymd(2026, 3, 13),
        source="fixture",
        name="Round Trip",
        positions=(
            StoredPosition(
                "US1234567890",
                quantity=Decimal("100"),
                metadata={"desk": "macro", "strategy": "core"},
            ),
        ),
    )

    codec = JsonCodec()
    assert codec.decode(codec.encode(portfolio)) == portfolio

    with SQLiteStorageAdapter(":memory:") as storage:
        assert storage.codec.decode(storage.codec.encode(portfolio)) == portfolio


def test_stored_position_requires_quantity_or_weight() -> None:
    with pytest.raises(ValueError, match="requires either quantity or weight"):
        StoredPosition("US1234567890")
