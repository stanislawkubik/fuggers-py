"""Funding reference-data records."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py._core.ids import InstrumentId
from fuggers_py._core.types import Currency


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class RepoReferenceData:
    """Repo reference record with raw decimal haircut semantics."""

    instrument_id: InstrumentId
    currency: Currency = Currency.USD
    collateral_currency: Currency | None = None
    term: str | None = None
    collateral_type: str | None = None
    haircut: Decimal | None = None
    settlement_lag_days: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.term is not None:
            object.__setattr__(self, "term", self.term.strip().upper())
        if self.collateral_type is not None:
            object.__setattr__(self, "collateral_type", self.collateral_type.strip())
        if self.haircut is not None:
            object.__setattr__(self, "haircut", _to_decimal(self.haircut))


__all__ = ["RepoReferenceData"]
