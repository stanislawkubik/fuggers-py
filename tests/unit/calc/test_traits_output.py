from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._core import Date
from fuggers_py._calc import BondQuoteOutput
from fuggers_py._core import InstrumentId


def test_bond_quote_output_optional_fields_and_repr() -> None:
    fixed = BondQuoteOutput(
        instrument_id=InstrumentId("FIXED"),
        clean_price=Decimal("101.25"),
        dirty_price=Decimal("102.00"),
        yield_to_maturity=Decimal("0.041"),
        modified_duration=Decimal("4.20"),
        dv01=Decimal("0.042"),
    )
    callable_output = BondQuoteOutput(
        instrument_id=InstrumentId("CALL"),
        oas=Decimal("0.0085"),
        effective_duration=Decimal("5.10"),
        effective_convexity=Decimal("28.0"),
        option_value=Decimal("1.12"),
    )
    frn = BondQuoteOutput(
        instrument_id=InstrumentId("FRN"),
        discount_margin=Decimal("0.0100"),
        projected_next_coupon=Decimal("1.31"),
        next_reset_date=Date.from_ymd(2026, 1, 15),
    )

    assert fixed.oas is None
    assert callable_output.clean_price is None
    assert frn.modified_duration is None
    assert "BondQuoteOutput" in repr(fixed)
    assert fixed.instrument_id == InstrumentId("FIXED")


def test_bond_quote_output_symmetric_dv01_pv01_backfill() -> None:
    from_dv01 = BondQuoteOutput(dv01="0.042")
    from_pv01 = BondQuoteOutput(pv01="0.042")

    assert from_dv01.dv01 == Decimal("0.042")
    assert from_dv01.pv01 == Decimal("0.042")
    assert from_pv01.dv01 == Decimal("0.042")
    assert from_pv01.pv01 == Decimal("0.042")


def test_bond_quote_output_rejects_mismatched_dv01_pv01() -> None:
    with pytest.raises(ValueError, match="dv01 and pv01"):
        BondQuoteOutput(dv01="0.042", pv01="0.041")
