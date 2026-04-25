"""CPI history records, parsers, and in-memory storage."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Any

from fuggers_py._core import YearMonth
from fuggers_py._core.types import Date


def _parse_decimal(value: object) -> Decimal:
    return Decimal(str(value).strip())


@dataclass(frozen=True, slots=True)
class InflationFixing:
    """Monthly inflation fixing keyed by index and observation month."""

    index_name: str
    observation_month: YearMonth
    value: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "index_name", self.index_name.strip().upper())
        object.__setattr__(self, "observation_month", YearMonth.parse(self.observation_month))
        object.__setattr__(self, "value", _parse_decimal(self.value))


@dataclass(slots=True)
class InMemoryInflationFixingSource:
    """Deterministic in-memory inflation fixing source."""

    fixings: dict[tuple[str, YearMonth], InflationFixing]

    def __init__(self, fixings: tuple[InflationFixing, ...] | list[InflationFixing] | None = None) -> None:
        self.fixings = {}
        for fixing in fixings or ():
            self.add_inflation_fixing(fixing)

    def add_inflation_fixing(self, fixing: InflationFixing) -> "InMemoryInflationFixingSource":
        self.fixings[(fixing.index_name, fixing.observation_month)] = fixing
        return self

    def get_inflation_fixing(self, index_name: str, observation_month: YearMonth | str) -> InflationFixing | None:
        return self.fixings.get((index_name.strip().upper(), YearMonth.parse(observation_month)))


InflationFixingSourceLike = object


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.strip().lower())


def _normalize_row(row: dict[str, Any]) -> dict[str, object]:
    return {_normalize_key(str(key)): value for key, value in row.items()}


def _resolve_month(value: object) -> YearMonth:
    text = str(value).strip()
    if len(text) == 7:
        return YearMonth.parse(text)
    parsed = Date.parse(text)
    return YearMonth(parsed.year(), parsed.month())


def _require_row_value(row: dict[str, object], aliases: tuple[str, ...], *, label: str) -> object:
    for alias in aliases:
        value = row.get(alias)
        if value not in (None, ""):
            return value
    raise ValueError(f"Monthly CPI row requires {label}.")


def _fixing_from_normalized_row(row: dict[str, object], *, index_name: str) -> InflationFixing:
    return InflationFixing(
        index_name=index_name,
        observation_month=_resolve_month(
            _require_row_value(
                row,
                ("observationmonth", "month", "date", "referencemonth"),
                label="an observation_month/month/date/reference_month field",
            )
        ),
        value=_require_row_value(
            row,
            ("value", "cpi", "referencecpi", "indexlevel", "cpurnsa"),
            label="a value/cpi/reference_cpi/index_level field",
        ),
    )


def parse_monthly_cpi_fixings_csv(text: str, *, index_name: str = "CPURNSA") -> tuple[InflationFixing, ...]:
    """Parse normalized monthly CPI CSV rows into ``InflationFixing`` records."""

    reader = csv.DictReader(StringIO(text.strip()))
    return tuple(_fixing_from_normalized_row(_normalize_row(raw_row), index_name=index_name) for raw_row in reader)


def parse_monthly_cpi_fixings_json(
    payload: str | bytes | list[dict[str, Any]] | dict[str, Any],
    *,
    index_name: str = "CPURNSA",
) -> tuple[InflationFixing, ...]:
    """Parse normalized monthly CPI JSON rows into ``InflationFixing`` records."""

    data: object
    if isinstance(payload, (str, bytes, bytearray)):
        data = json.loads(payload)
    else:
        data = payload
    if isinstance(data, dict):
        rows = data.get("data") or data.get("observations") or data.get("fixings") or []
    else:
        rows = data
    if not isinstance(rows, list):
        raise ValueError("Monthly CPI JSON payload must be a list or contain a list under data/observations/fixings.")
    fixings: list[InflationFixing] = []
    for raw_row in rows:
        if not isinstance(raw_row, dict):
            raise ValueError("Monthly CPI JSON rows must be objects.")
        fixings.append(_fixing_from_normalized_row(_normalize_row(raw_row), index_name=index_name))
    return tuple(fixings)


def load_monthly_cpi_fixings_csv(path: str | Path, *, index_name: str = "CPURNSA") -> tuple[InflationFixing, ...]:
    """Load normalized monthly CPI CSV rows from disk."""

    return parse_monthly_cpi_fixings_csv(Path(path).read_text(), index_name=index_name)


def load_monthly_cpi_fixings_json(path: str | Path, *, index_name: str = "CPURNSA") -> tuple[InflationFixing, ...]:
    """Load normalized monthly CPI JSON rows from disk."""

    return parse_monthly_cpi_fixings_json(Path(path).read_text(), index_name=index_name)


def parse_bls_cpi_json(
    payload: str | bytes | dict[str, Any] | list[dict[str, Any]],
    *,
    index_name: str = "CPURNSA",
) -> tuple[InflationFixing, ...]:
    """Parse monthly BLS CPI-U JSON content into ``InflationFixing`` records."""

    data: object
    if isinstance(payload, (str, bytes, bytearray)):
        data = json.loads(payload)
    else:
        data = payload

    rows: object
    if isinstance(data, dict) and isinstance(data.get("Results"), dict):
        series = data["Results"].get("series")  # type: ignore[index]
        if not isinstance(series, list) or not series:
            raise ValueError("BLS CPI JSON payload requires Results.series with at least one series.")
        first_series = series[0]
        if not isinstance(first_series, dict):
            raise ValueError("BLS CPI JSON series entries must be objects.")
        rows = first_series.get("data", [])
    elif isinstance(data, dict):
        rows = data.get("data") or data.get("observations") or []
    else:
        rows = data

    if not isinstance(rows, list):
        raise ValueError("BLS CPI JSON payload must contain a list of monthly observation rows.")

    fixings: list[InflationFixing] = []
    for raw_row in rows:
        if not isinstance(raw_row, dict):
            raise ValueError("BLS CPI rows must be objects.")
        row = _normalize_row(raw_row)
        period = str(_require_row_value(row, ("period",), label="a period field")).strip().upper()
        if period == "M13":
            continue
        if not re.fullmatch(r"M(0[1-9]|1[0-2])", period):
            raise ValueError(f"BLS CPI row requires a monthly period M01-M12; received {period!r}.")
        year = int(str(_require_row_value(row, ("year",), label="a year field")).strip())
        month = int(period[1:])
        fixings.append(
            InflationFixing(
                index_name=index_name,
                observation_month=YearMonth(year, month),
                value=_require_row_value(row, ("value",), label="a value field"),
            )
        )
    return tuple(fixings)


def parse_fred_cpi_csv(text: str, *, index_name: str = "CPURNSA") -> tuple[InflationFixing, ...]:
    """Parse a FRED monthly CPI CSV export into ``InflationFixing`` records."""

    reader = csv.DictReader(StringIO(text.strip()))
    fixings: list[InflationFixing] = []
    for raw_row in reader:
        row = _normalize_row(raw_row)
        date_value = _require_row_value(row, ("date", "observationdate"), label="a DATE field")
        value_key = next(
            (
                key
                for key, value in row.items()
                if key not in {"date", "observationdate"} and value not in (None, "")
            ),
            None,
        )
        if value_key is None:
            raise ValueError("FRED CPI row requires a CPI value column alongside DATE.")
        fixings.append(
            InflationFixing(
                index_name=index_name,
                observation_month=_resolve_month(date_value),
                value=row[value_key],
            )
        )
    return tuple(fixings)


def treasury_cpi_source_from_fixings(
    fixings: tuple[InflationFixing, ...] | list[InflationFixing],
) -> InMemoryInflationFixingSource:
    """Build an in-memory inflation fixing source from parsed CPI history."""

    return InMemoryInflationFixingSource(fixings)


parse_treasury_cpi_fixings_csv = parse_monthly_cpi_fixings_csv
parse_treasury_cpi_fixings_json = parse_monthly_cpi_fixings_json
load_treasury_cpi_fixings_csv = load_monthly_cpi_fixings_csv
load_treasury_cpi_fixings_json = load_monthly_cpi_fixings_json


__all__ = [
    "InMemoryInflationFixingSource",
    "InflationFixing",
    "InflationFixingSourceLike",
    "load_monthly_cpi_fixings_csv",
    "load_monthly_cpi_fixings_json",
    "load_treasury_cpi_fixings_csv",
    "load_treasury_cpi_fixings_json",
    "parse_bls_cpi_json",
    "parse_fred_cpi_csv",
    "parse_monthly_cpi_fixings_csv",
    "parse_monthly_cpi_fixings_json",
    "parse_treasury_cpi_fixings_csv",
    "parse_treasury_cpi_fixings_json",
    "treasury_cpi_source_from_fixings",
]
