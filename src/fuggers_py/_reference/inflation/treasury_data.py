"""Deterministic monthly CPI adapters for fixture-driven inflation workflows.

The helpers in this module parse normalized monthly CPI rows into
``InflationFixing`` records. They are suitable for synthetic fixtures and for
monthly CPI history downloaded from BLS or FRED after normalization.

They are intentionally not a full parser for Treasury auctioned-security rows.
Use :mod:`fuggers_py._reference.inflation.treasury_auction_data` for Treasury
auctioned TIPS metadata.
"""

from __future__ import annotations

import csv
import json
import re
from io import StringIO
from pathlib import Path
from typing import Any

from fuggers_py._core.types import Date
from fuggers_py._core import YearMonth
from fuggers_py._market.snapshot import InflationFixing
from fuggers_py._market.sources import InMemoryInflationFixingSource


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.strip().lower())


def _normalize_row(row: dict[str, Any]) -> dict[str, object]:
    return {_normalize_key(str(key)): value for key, value in row.items()}


def _resolve_month(value: object) -> YearMonth:
    text = str(value).strip()
    if len(text) == 7:
        return YearMonth.parse(text)
    return YearMonth(Date.parse(text).year(), Date.parse(text).month())


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
    """Parse normalized monthly CPI CSV rows into ``InflationFixing`` records.

    The CSV should contain one row per observation month and a value column.
    The helper expects the feed to be normalized already; it does not attempt
    to infer Treasury auction metadata.
    """

    reader = csv.DictReader(StringIO(text.strip()))
    return tuple(
        _fixing_from_normalized_row(_normalize_row(raw_row), index_name=index_name)
        for raw_row in reader
    )


def parse_monthly_cpi_fixings_json(
    payload: str | bytes | list[dict[str, Any]] | dict[str, Any],
    *,
    index_name: str = "CPURNSA",
) -> tuple[InflationFixing, ...]:
    """Parse normalized monthly CPI JSON rows into ``InflationFixing`` records.

    The payload may be a list of row objects or a dictionary containing rows
    under ``data``, ``observations``, or ``fixings``.
    """

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
    """Parse monthly BLS CPI-U JSON content into ``InflationFixing`` records.

    Supported inputs are either raw BLS API payloads with
    ``Results.series[].data[]`` records or a normalized list of row objects with
    ``year`` / ``period`` / ``value`` fields.
    """

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
    """Parse a FRED monthly CPI CSV export into ``InflationFixing`` records.

    The CSV is expected to look like the standard FRED download format with a
    ``DATE`` column and one CPI series column such as ``CPIAUCNS``.
    """

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


# Backwards-compatible aliases kept at the module level for callers that still
# import the pre-polish names directly.
parse_treasury_cpi_fixings_csv = parse_monthly_cpi_fixings_csv
parse_treasury_cpi_fixings_json = parse_monthly_cpi_fixings_json
load_treasury_cpi_fixings_csv = load_monthly_cpi_fixings_csv
load_treasury_cpi_fixings_json = load_monthly_cpi_fixings_json


__all__ = [
    "load_monthly_cpi_fixings_csv",
    "load_monthly_cpi_fixings_json",
    "parse_bls_cpi_json",
    "parse_fred_cpi_csv",
    "parse_monthly_cpi_fixings_csv",
    "parse_monthly_cpi_fixings_json",
    "treasury_cpi_source_from_fixings",
]
