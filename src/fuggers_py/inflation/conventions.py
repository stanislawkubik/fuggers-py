"""Inflation index conventions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from fuggers_py._core.types import Currency

from .errors import InflationError, InvalidObservationLag


class InflationInterpolation(StrEnum):
    """Interpolation convention for inflation fixings."""

    MONTHLY = "MONTHLY"
    LINEAR = "LINEAR"
    FLAT = "FLAT"


def _normalize_aliases(aliases: tuple[str, ...]) -> tuple[str, ...]:
    ordered: dict[str, None] = {}
    for alias in aliases:
        normalized = str(alias).strip().upper()
        if normalized:
            ordered[normalized] = None
    return tuple(ordered)


@dataclass(frozen=True, slots=True)
class InflationConvention:
    """Generic inflation-index definition used by reference-index helpers."""

    name: str
    family: str
    currency: Currency
    index_source: str
    observation_lag_months: int
    interpolation_method: InflationInterpolation = InflationInterpolation.MONTHLY
    publication_style: str | None = None
    aliases: tuple[str, ...] = ()
    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "family", self.family.strip().upper())
        object.__setattr__(self, "index_source", self.index_source.strip().upper())
        object.__setattr__(self, "observation_lag_months", int(self.observation_lag_months))
        object.__setattr__(self, "aliases", _normalize_aliases(tuple(self.aliases)))
        if self.publication_style is not None:
            object.__setattr__(self, "publication_style", self.publication_style.strip().upper())
        if self.notes is not None:
            object.__setattr__(self, "notes", self.notes.strip())
        if self.observation_lag_months < 0:
            raise InvalidObservationLag(self.observation_lag_months)

    def lookup_names(self) -> tuple[str, ...]:
        """Return the ordered source names accepted when resolving fixings."""

        return tuple(dict.fromkeys((self.index_source, *self.aliases)))


InflationIndexDefinition = InflationConvention


USD_CPI_U_NSA = InflationConvention(
    name="USD CPI-U NSA",
    family="CPI_U",
    currency=Currency.USD,
    index_source="CPURNSA",
    observation_lag_months=3,
    interpolation_method=InflationInterpolation.LINEAR,
    publication_style="NSA",
    aliases=("CPI-U", "CPI-U NSA", "US CPI-U", "US CPI-U NSA"),
    notes=(
        "US Consumer Price Index for All Urban Consumers, Not Seasonally Adjusted. "
        "Reference CPI uses the third preceding month with linear daily interpolation."
    ),
)


__all__ = [
    "InflationConvention",
    "InflationError",
    "InflationIndexDefinition",
    "InflationInterpolation",
    "InvalidObservationLag",
    "USD_CPI_U_NSA",
]
