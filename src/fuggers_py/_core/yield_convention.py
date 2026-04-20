"""Shared yield and accrued conventions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import InvalidBondSpec


class YieldConvention(str, Enum):
    """Yield convention vocabulary."""

    STREET_CONVENTION = "STREET_CONVENTION"
    TRUE_YIELD = "TRUE_YIELD"
    ISMA = "ISMA"
    SIMPLE_YIELD = "SIMPLE_YIELD"
    DISCOUNT_YIELD = "DISCOUNT_YIELD"
    BOND_EQUIVALENT_YIELD = "BOND_EQUIVALENT_YIELD"
    MUNICIPAL_YIELD = "MUNICIPAL_YIELD"
    MOOSMULLER = "MOOSMULLER"
    BRAESS_FANGMEYER = "BRAESS_FANGMEYER"
    ANNUAL = "ANNUAL"
    CONTINUOUS = "CONTINUOUS"

    @classmethod
    def default(cls) -> "YieldConvention":
        return cls.STREET_CONVENTION


class AccruedConvention(str, Enum):
    """Convention used to compute accrued interest."""

    STANDARD = "STANDARD"
    USING_YEAR_FRACTION = "USING_YEAR_FRACTION"
    ISMA = "ISMA"
    EX_DIVIDEND = "EX_DIVIDEND"
    RECORD_DATE = "RECORD_DATE"
    CUM_DIVIDEND = "CUM_DIVIDEND"
    NONE = "NONE"

    @classmethod
    def default(cls) -> "AccruedConvention":
        return cls.STANDARD


class RoundingKind(str, Enum):
    """Supported rounding strategies for reported yields."""

    NONE = "NONE"
    DECIMAL_PLACES = "DECIMAL_PLACES"


@dataclass(frozen=True, slots=True)
class RoundingConvention:
    """Rounding rule applied to solved yields."""

    kind: RoundingKind
    digits: int = 0

    @classmethod
    def none(cls) -> "RoundingConvention":
        return cls(RoundingKind.NONE, digits=0)

    @classmethod
    def decimal_places(cls, digits: int) -> "RoundingConvention":
        d = int(digits)
        if d < 0:
            raise InvalidBondSpec(reason="RoundingConvention.decimal_places requires digits >= 0.")
        return cls(RoundingKind.DECIMAL_PLACES, digits=d)

    def apply(self, value: float) -> float:
        if self.kind is RoundingKind.NONE:
            return float(value)
        if self.kind is RoundingKind.DECIMAL_PLACES:
            return round(float(value), self.digits)
        raise InvalidBondSpec(reason=f"Unknown rounding convention: {self.kind!r}.")  # pragma: no cover


__all__ = [
    "YieldConvention",
    "AccruedConvention",
    "RoundingConvention",
    "RoundingKind",
]
