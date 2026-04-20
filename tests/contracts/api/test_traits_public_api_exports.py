from __future__ import annotations

from decimal import Decimal

from fuggers_py import Date, Tenor


def test_traits_root_reexports_tenor() -> None:
    assert str(Tenor.parse("5Y")) == "5Y"
    assert Tenor.parse("2Y").add_to(Date.from_ymd(2026, 1, 15)) == Date.from_ymd(2028, 1, 15)
