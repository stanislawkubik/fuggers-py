from __future__ import annotations

from decimal import Decimal

from fuggers_py._core import Currency, Date
from fuggers_py._runtime import QuoteSide
from fuggers_py._core import CurveId, InstrumentId
from fuggers_py._runtime.quotes import RawQuote
from fuggers_py._runtime.snapshot import CurveInputs, CurvePoint, IndexFixing
from fuggers_py._runtime.sources import InMemoryFixingSource, InMemoryQuoteSource


def test_raw_quote_curve_inputs_and_fixing_sources() -> None:
    instrument_id = InstrumentId("US0000000001")
    quote = RawQuote(
        instrument_id=instrument_id,
        value=Decimal("101.25"),
        as_of=Date.from_ymd(2026, 1, 15),
        currency=Currency.USD,
    )
    assert quote.as_of == Date.from_ymd(2026, 1, 15)
    assert quote.mid == Decimal("101.25")

    inputs = CurveInputs.from_points(
        CurveId("usd.discount"),
        Date.from_ymd(2026, 1, 15),
        [
            CurvePoint(Decimal("5.0"), Decimal("0.04")),
            CurvePoint(Decimal("1.0"), Decimal("0.045")),
            CurvePoint(Decimal("2.0"), Decimal("0.043")),
        ],
    )
    assert list(inputs.tenors()) == [Decimal("1.0"), Decimal("2.0"), Decimal("5.0")]

    quote_source = InMemoryQuoteSource([quote])
    assert quote_source.get_quote(instrument_id, QuoteSide.MID) == quote

    fixing = IndexFixing("SOFR", Date.from_ymd(2026, 1, 14), Decimal("0.0410"))
    fixing_source = InMemoryFixingSource([fixing])
    assert fixing_source.get_fixing("SOFR", Date.from_ymd(2026, 1, 14)) == fixing
    assert fixing_source.get_rate("SOFR", Date.from_ymd(2026, 1, 14)) == Decimal("0.0410")
