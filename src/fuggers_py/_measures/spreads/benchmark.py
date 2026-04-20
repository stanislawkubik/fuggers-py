"""Benchmark specification (`fuggers_py._measures.spreads.benchmark`)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from fuggers_py._core import Tenor


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class BenchmarkKind(str, Enum):
    """Benchmark selection mode for government-curve comparisons."""

    INTERPOLATED = "INTERPOLATED"
    NEAREST = "NEAREST"
    TENOR = "TENOR"
    EXPLICIT = "EXPLICIT"


@dataclass(frozen=True, slots=True)
class BenchmarkSpec:
    """Government-curve benchmark selection and explicit override.

    Attributes
    ----------
    kind
        Benchmark selection mode.
    tenor
        Optional tenor used when ``kind`` is ``TENOR``.
    explicit_yield
        Raw decimal benchmark yield used when ``kind`` is ``EXPLICIT``.
    """

    kind: BenchmarkKind
    tenor: Tenor | None = None
    explicit_yield: Decimal | None = None

    @classmethod
    def interpolated(cls) -> "BenchmarkSpec":
        """Select the interpolated government-curve yield."""
        return cls(BenchmarkKind.INTERPOLATED)

    @classmethod
    def nearest(cls) -> "BenchmarkSpec":
        """Select the nearest benchmark tenor."""
        return cls(BenchmarkKind.NEAREST)

    @classmethod
    def ten_year(cls) -> "BenchmarkSpec":
        """Select the 10Y benchmark tenor."""
        return cls(BenchmarkKind.TENOR, tenor=Tenor.parse("10Y"))

    @classmethod
    def five_year(cls) -> "BenchmarkSpec":
        """Select the 5Y benchmark tenor."""
        return cls(BenchmarkKind.TENOR, tenor=Tenor.parse("5Y"))

    @classmethod
    def explicit(cls, yield_value: object) -> "BenchmarkSpec":
        """Select an explicit raw-decimal benchmark yield."""
        return cls(BenchmarkKind.EXPLICIT, explicit_yield=_to_decimal(yield_value))

    def description(self) -> str:
        """Return a human-readable benchmark description."""
        if self.kind is BenchmarkKind.EXPLICIT and self.explicit_yield is not None:
            return f"Explicit benchmark ({self.explicit_yield} decimal)"
        if self.kind is BenchmarkKind.TENOR and self.tenor is not None:
            return f"Benchmark tenor {self.tenor}"
        return self.kind.value.replace("_", " ").title()

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.description()


__all__ = ["BenchmarkSpec", "BenchmarkKind"]
