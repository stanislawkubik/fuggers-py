"""Credit reference-data records."""

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
class CdsReferenceData:
    """CDS reference record with raw decimal coupon and recovery fields."""

    instrument_id: InstrumentId
    reference_entity: str
    currency: Currency = Currency.USD
    tenor: str | None = None
    seniority: str | None = None
    restructuring_clause: str | None = None
    coupon: Decimal | None = None
    recovery_rate: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        object.__setattr__(self, "reference_entity", self.reference_entity.strip())
        if self.tenor is not None:
            object.__setattr__(self, "tenor", self.tenor.strip().upper())
        if self.seniority is not None:
            object.__setattr__(self, "seniority", self.seniority.strip().upper())
        if self.restructuring_clause is not None:
            object.__setattr__(self, "restructuring_clause", self.restructuring_clause.strip().upper())
        if self.coupon is not None:
            object.__setattr__(self, "coupon", _to_decimal(self.coupon))
        if self.recovery_rate is not None:
            object.__setattr__(self, "recovery_rate", _to_decimal(self.recovery_rate))


__all__ = ["CdsReferenceData"]
