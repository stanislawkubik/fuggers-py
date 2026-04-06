from __future__ import annotations

from fuggers_py.core import CurveId, EtfId, InstrumentId, PortfolioId


def test_typed_ids_roundtrip_hash_and_dict_usage() -> None:
    instrument_id = InstrumentId("US1234567890")
    curve_id = CurveId.parse("usd.discount")
    portfolio_id = PortfolioId.from_string("core-book")
    etf_id = EtfId("agg-usd")

    assert str(instrument_id) == "US1234567890"
    assert CurveId.from_string(str(curve_id)) == curve_id
    assert PortfolioId.parse(str(portfolio_id)) == portfolio_id
    assert EtfId.parse(str(etf_id)) == etf_id

    mapping = {
        instrument_id: "bond",
        curve_id: "curve",
        portfolio_id: "portfolio",
        etf_id: "etf",
    }
    assert mapping[InstrumentId("US1234567890")] == "bond"
    assert mapping[CurveId("usd.discount")] == "curve"
    assert "InstrumentId" in repr(instrument_id)
    assert "CurveId" in repr(curve_id)
