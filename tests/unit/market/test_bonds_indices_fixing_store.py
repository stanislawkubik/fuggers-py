from __future__ import annotations

from decimal import Decimal

from fuggers_py.rates import IndexFixing, IndexFixingStore, IndexSource
from fuggers_py._core import Date


def test_add_and_get_fixing() -> None:
    store = IndexFixingStore()
    fixing_date = Date.from_ymd(2024, 1, 2)
    store.add_fixing("SOFR", fixing_date, Decimal("0.051"))
    assert store.get_fixing("SOFR", fixing_date) == IndexFixing("SOFR", fixing_date, Decimal("0.051"))


def test_missing_fixing() -> None:
    store = IndexFixingStore()
    assert store.get_fixing("SOFR", Date.from_ymd(2024, 1, 2)) is None


def test_get_range() -> None:
    store = IndexFixingStore.from_rates(
        "SOFR",
        {
            Date.from_ymd(2024, 1, 2): Decimal("0.05"),
            Date.from_ymd(2024, 1, 3): Decimal("0.051"),
            Date.from_ymd(2024, 1, 4): Decimal("0.052"),
        },
    )
    result = store.get_range("SOFR", Date.from_ymd(2024, 1, 2), Date.from_ymd(2024, 1, 3))
    assert [item.fixing_date for item in result] == [Date.from_ymd(2024, 1, 2), Date.from_ymd(2024, 1, 3)]


def test_last_fixing_before() -> None:
    store = IndexFixingStore.from_rates(
        "SOFR",
        [
            (Date.from_ymd(2024, 1, 2), Decimal("0.05")),
            (Date.from_ymd(2024, 1, 4), Decimal("0.052")),
        ],
    )
    last = store.last_fixing_before("SOFR", Date.from_ymd(2024, 1, 5))
    assert last is not None
    assert last.fixing_date == Date.from_ymd(2024, 1, 4)


def test_multiple_indices() -> None:
    store = IndexFixingStore()
    store.add_fixing("SOFR", Date.from_ymd(2024, 1, 2), Decimal("0.05"))
    store.add_fixing("SONIA", Date.from_ymd(2024, 1, 2), Decimal("0.049"))
    assert store.indices() == ("SOFR", "SONIA")


def test_count_and_has_index() -> None:
    store = IndexFixingStore()
    store.add_fixing("SOFR", Date.from_ymd(2024, 1, 2), Decimal("0.05"))
    store.add_fixing("SOFR", Date.from_ymd(2024, 1, 3), Decimal("0.051"))
    assert store.count() == 2
    assert store.count("SOFR") == 2
    assert store.has_index("SOFR")
    assert not store.has_index("ESTR")


def test_index_fixing_struct() -> None:
    fixing = IndexFixing(
        "sofr",
        Date.from_ymd(2024, 1, 2),
        Decimal("0.05"),
        source=IndexSource.PUBLICATION,
    )
    assert fixing.index_name == "SOFR"
    assert fixing.source is IndexSource.PUBLICATION


def test_from_rates() -> None:
    store = IndexFixingStore.from_rates(
        "SOFR",
        [(Date.from_ymd(2024, 1, 2), Decimal("0.05")), (Date.from_ymd(2024, 1, 3), Decimal("0.051"))],
    )
    assert store.count("SOFR") == 2


def test_clear() -> None:
    store = IndexFixingStore.from_rates("SOFR", {Date.from_ymd(2024, 1, 2): Decimal("0.05")})
    store.clear()
    assert store.count() == 0
