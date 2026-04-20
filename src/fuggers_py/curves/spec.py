"""Public identity record for one calibrated rates curve snapshot."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from fuggers_py._core.types import Currency, Date

from .errors import InvalidCurveInput
from .enums import CurveType, ExtrapolationPolicy


def _normalize_name(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise InvalidCurveInput(f"{field_name} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise InvalidCurveInput(f"{field_name} must be a non-empty string.")
    return normalized


def _normalize_reference_date(value: Date | dt.date) -> Date:
    if isinstance(value, Date):
        return value
    if isinstance(value, dt.date):
        return Date(value)
    raise InvalidCurveInput("reference_date must be a fuggers_py._core.types.Date or datetime.date.")


def _normalize_currency(value: Currency | str) -> Currency:
    if isinstance(value, Currency):
        return value
    if isinstance(value, str):
        return Currency.from_code(value)
    raise InvalidCurveInput("currency must be a Currency or ISO currency code string.")


@dataclass(frozen=True, slots=True)
class CurveSpec:
    """Immutable business identity for one public rates curve snapshot."""

    name: str
    reference_date: Date | dt.date
    day_count: str
    currency: Currency | str
    type: CurveType
    reference: str | None = None
    extrapolation_policy: ExtrapolationPolicy = ExtrapolationPolicy.ERROR

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _normalize_name(self.name, field_name="name"))
        object.__setattr__(self, "reference_date", _normalize_reference_date(self.reference_date))
        object.__setattr__(self, "day_count", _normalize_name(self.day_count, field_name="day_count").upper())
        object.__setattr__(self, "currency", _normalize_currency(self.currency))
        if not isinstance(self.type, CurveType):
            raise InvalidCurveInput("type must be a CurveType.")
        if not isinstance(self.extrapolation_policy, ExtrapolationPolicy):
            raise InvalidCurveInput("extrapolation_policy must be an ExtrapolationPolicy.")
        if self.reference is not None:
            normalized_reference = self.reference.strip()
            object.__setattr__(self, "reference", normalized_reference or None)


__all__ = ["CurveSpec"]
