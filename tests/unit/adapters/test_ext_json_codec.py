from __future__ import annotations

from decimal import Decimal

from fuggers_py.bonds.types import BondType, IssuerType
from fuggers_py._core import Currency, Date, Frequency
from fuggers_py._storage import JsonCodec, PrettyJsonCodec
from fuggers_py._core import InstrumentId
from fuggers_py._reference import BondReferenceData


def test_json_codec_round_trips_nested_dataclass_payloads() -> None:
    payload = {
        "reference": BondReferenceData(
            instrument_id=InstrumentId("CODEC-1"),
            bond_type=BondType.FIXED_RATE,
            issuer_type=IssuerType.CORPORATE,
            issue_date=Date.from_ymd(2024, 1, 15),
            maturity_date=Date.from_ymd(2031, 1, 15),
            currency=Currency.USD,
            coupon_rate=Decimal("0.0450"),
            frequency=Frequency.SEMI_ANNUAL,
            issuer_name="Codec Corp",
        ),
        "values": (Decimal("1.25"), Date.from_ymd(2026, 3, 13), BondType.CALLABLE),
    }

    decoded = JsonCodec().decode(JsonCodec().encode(payload))

    assert decoded == payload


def test_pretty_json_codec_is_human_readable_and_round_trips() -> None:
    codec = PrettyJsonCodec()

    encoded = codec.encode({"a": Decimal("1.0"), "b": Date.from_ymd(2026, 3, 13)})
    decoded = codec.decode(encoded)

    assert b"\n" in encoded
    assert decoded["a"] == Decimal("1.0")
    assert decoded["b"] == Date.from_ymd(2026, 3, 13)
