"""Inflation conventions, CPI helpers, and Treasury adapters."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, replace
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Any

from fuggers_py._core import YearMonth
from fuggers_py._core.errors import FuggersError
from fuggers_py._core.ids import YearMonth as YearMonthId
from fuggers_py._core.types import Currency, Date
from fuggers_py._inflation_types import InflationInterpolation
from fuggers_py.bonds import TipsBond


def _normalize_aliases(aliases: tuple[str, ...]) -> tuple[str, ...]:
    ordered: dict[str, None] = {}
    for alias in aliases:
        normalized = str(alias).strip().upper()
        if normalized:
            ordered[normalized] = None
    return tuple(ordered)


@dataclass(frozen=True, slots=True)
class InflationError(FuggersError):
    """Base exception for inflation-convention and reference-index failures."""


@dataclass(frozen=True, slots=True)
class InvalidObservationLag(InflationError):
    """Raised when an inflation convention carries an invalid observation lag."""

    observation_lag_months: int

    def __str__(self) -> str:  # pragma: no cover - trivial
        return (
            "Invalid inflation observation lag: "
            f"{self.observation_lag_months}. observation_lag_months must be non-negative."
        )


@dataclass(frozen=True, slots=True)
class UnsupportedInflationInterpolation(InflationError):
    """Raised when reference-index resolution does not support the convention."""

    interpolation_method: object

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Unsupported inflation interpolation method: {self.interpolation_method!r}."


@dataclass(frozen=True, slots=True)
class MissingInflationFixing(InflationError):
    """Raised when required monthly inflation fixings are not available."""

    index_name: str
    requested_date: Date
    observation_months: tuple[YearMonthId, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "index_name", self.index_name.strip().upper())
        object.__setattr__(
            self,
            "observation_months",
            tuple(YearMonth.parse(observation_month) for observation_month in self.observation_months),
        )

    def __str__(self) -> str:  # pragma: no cover - trivial
        months = ", ".join(observation_month.as_str() for observation_month in self.observation_months)
        return (
            f"Missing inflation fixing for {self.index_name} required to resolve reference CPI on "
            f"{self.requested_date}: {months}."
        )


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


def _year_month(value: Date) -> YearMonth:
    return YearMonth(value.year(), value.month())


def _resolve_fixing_source(fixing_source: InflationFixingSourceLike) -> object:
    if hasattr(fixing_source, "inflation_fixing_source"):
        inflation_fixing_source = fixing_source.inflation_fixing_source
        if callable(inflation_fixing_source):
            return inflation_fixing_source()
        return inflation_fixing_source
    if hasattr(fixing_source, "get_inflation_fixing"):
        return fixing_source
    raise TypeError("fixing_source must provide get_inflation_fixing() or be a MarketDataSnapshot.")


def _validate_observation_lag(observation_lag_months: int) -> None:
    if observation_lag_months < 0:
        raise InvalidObservationLag(observation_lag_months)


def _lookup_fixing(
    observation_month: YearMonth,
    *,
    convention: InflationConvention,
    fixing_source: object,
) -> InflationFixing | None:
    for index_name in convention.lookup_names():
        fixing = fixing_source.get_inflation_fixing(index_name, observation_month)
        if fixing is not None:
            return fixing
    return None


def _require_fixings(
    observation_months: tuple[YearMonth, ...],
    *,
    settlement_date: Date,
    convention: InflationConvention,
    fixing_source: object,
) -> tuple[InflationFixing, ...]:
    resolved: list[InflationFixing] = []
    missing: list[YearMonth] = []

    for observation_month in observation_months:
        fixing = _lookup_fixing(
            observation_month,
            convention=convention,
            fixing_source=fixing_source,
        )
        if fixing is None:
            missing.append(observation_month)
            continue
        resolved.append(fixing)

    if missing:
        raise MissingInflationFixing(
            index_name=convention.index_source,
            requested_date=settlement_date,
            observation_months=tuple(missing),
        )
    return tuple(resolved)


def reference_cpi(
    settlement_date: Date,
    convention: InflationConvention,
    fixing_source: InflationFixingSourceLike,
) -> Decimal:
    """Return the daily reference CPI implied by monthly published fixings."""

    _validate_observation_lag(convention.observation_lag_months)
    resolved_source = _resolve_fixing_source(fixing_source)
    month_start = settlement_date.start_of_month()
    first_month = _year_month(month_start.add_months(-convention.observation_lag_months))

    if convention.interpolation_method is InflationInterpolation.MONTHLY:
        fixing = _require_fixings(
            (first_month,),
            settlement_date=settlement_date,
            convention=convention,
            fixing_source=resolved_source,
        )[0]
        return fixing.value

    if convention.interpolation_method is InflationInterpolation.LINEAR:
        second_month = _year_month(month_start.add_months(1 - convention.observation_lag_months))
        first_fixing, second_fixing = _require_fixings(
            (first_month, second_month),
            settlement_date=settlement_date,
            convention=convention,
            fixing_source=resolved_source,
        )
        if settlement_date.day() == 1:
            return first_fixing.value

        month_length = Decimal(settlement_date.days_in_month())
        day_offset = Decimal(settlement_date.day() - 1)
        weight = day_offset / month_length
        return first_fixing.value + (second_fixing.value - first_fixing.value) * weight

    raise UnsupportedInflationInterpolation(convention.interpolation_method)


def reference_index_ratio(
    settlement_date: Date,
    base_date: Date,
    convention: InflationConvention,
    fixing_source: InflationFixingSourceLike,
) -> Decimal:
    """Return the ratio of reference CPI at settlement and base dates."""

    settlement_reference = reference_cpi(settlement_date, convention, fixing_source)
    base_reference = reference_cpi(base_date, convention, fixing_source)
    return settlement_reference / base_reference


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


def _require_value(row: dict[str, object], aliases: tuple[str, ...], *, label: str) -> object:
    for alias in aliases:
        value = row.get(alias)
        if value not in (None, ""):
            return value
    raise ValueError(f"Treasury auction row requires {label}.")


def _optional_value(row: dict[str, object], aliases: tuple[str, ...]) -> object | None:
    for alias in aliases:
        value = row.get(alias)
        if value not in (None, ""):
            return value
    return None


def _parse_date(value: object) -> Date:
    text = str(value).strip()
    return Date.parse(text.split("T", 1)[0])


def _parse_decimal(value: object) -> Decimal:
    return Decimal(str(value).strip())


def _is_tips_row(row: dict[str, object]) -> bool:
    if _optional_value(row, ("refcpionissuedate", "refcpiondateddate")) is not None:
        return True
    for value in row.values():
        if isinstance(value, str):
            text = value.strip().lower()
            if "tips" in text or "inflation protected" in text or "inflation-protected" in text:
                return True
    return False


@dataclass(frozen=True, slots=True)
class TreasuryAuctionedTipsRow:
    """Subset of Treasury auctioned-security TIPS metadata used by the library."""

    cusip: str
    security_type: str
    security_term: str
    issue_date: Date
    dated_date: Date | None
    maturity_date: Date
    coupon_rate: Decimal
    original_issue_date: Date | None = None
    ref_cpi_on_issue_date: Decimal | None = None
    ref_cpi_on_dated_date: Decimal | None = None
    original_security_term: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "cusip", self.cusip.strip().upper())
        object.__setattr__(self, "security_type", self.security_type.strip())
        object.__setattr__(self, "security_term", self.security_term.strip())
        object.__setattr__(self, "coupon_rate", _parse_decimal(self.coupon_rate))
        if self.original_security_term is not None:
            object.__setattr__(self, "original_security_term", self.original_security_term.strip())


def _row_from_normalized_payload(row: dict[str, object]) -> TreasuryAuctionedTipsRow:
    return TreasuryAuctionedTipsRow(
        cusip=str(_require_value(row, ("cusip",), label="a CUSIP field")).strip(),
        security_type=str(
            _require_value(
                row,
                ("securitytype", "securitytypedesc", "securitydescription"),
                label="a SecurityType field",
            )
        ).strip(),
        security_term=str(
            _require_value(
                row,
                ("securityterm", "securitytermweekyear", "securitytermyearmonth"),
                label="a SecurityTerm field",
            )
        ).strip(),
        issue_date=_parse_date(_require_value(row, ("issuedate",), label="an IssueDate field")),
        dated_date=(None if _optional_value(row, ("dateddate",)) is None else _parse_date(_optional_value(row, ("dateddate",)))),
        maturity_date=_parse_date(_require_value(row, ("maturitydate",), label="a MaturityDate field")),
        coupon_rate=_parse_decimal(
            _require_value(row, ("interestrate", "couponrate", "coupon"), label="an InterestRate/CouponRate field")
        ),
        original_issue_date=(
            None
            if _optional_value(row, ("originalissuedate",)) is None
            else _parse_date(_optional_value(row, ("originalissuedate",)))
        ),
        ref_cpi_on_issue_date=(
            None
            if _optional_value(row, ("refcpionissuedate",)) is None
            else _parse_decimal(_optional_value(row, ("refcpionissuedate",)))
        ),
        ref_cpi_on_dated_date=(
            None
            if _optional_value(row, ("refcpiondateddate",)) is None
            else _parse_decimal(_optional_value(row, ("refcpiondateddate",)))
        ),
        original_security_term=(
            None
            if _optional_value(row, ("originalsecurityterm",)) is None
            else str(_optional_value(row, ("originalsecurityterm",))).strip()
        ),
    )


def parse_treasury_auctioned_tips_json(
    payload: str | bytes | list[dict[str, Any]] | dict[str, Any],
) -> tuple[TreasuryAuctionedTipsRow, ...]:
    """Parse Treasury auctioned-security JSON rows and retain TIPS records only."""

    data: object
    if isinstance(payload, (str, bytes, bytearray)):
        data = json.loads(payload)
    else:
        data = payload
    if isinstance(data, dict):
        rows = data.get("data") or data.get("securities") or data.get("auctioned") or []
    else:
        rows = data
    if not isinstance(rows, list):
        raise ValueError("Treasury auctioned TIPS JSON payload must contain a list of row objects.")

    parsed_rows: list[TreasuryAuctionedTipsRow] = []
    for raw_row in rows:
        if not isinstance(raw_row, dict):
            raise ValueError("Treasury auctioned TIPS JSON rows must be objects.")
        normalized = _normalize_row(raw_row)
        if not _is_tips_row(normalized):
            continue
        parsed_rows.append(_row_from_normalized_payload(normalized))
    return tuple(parsed_rows)


def parse_treasury_auctioned_tips_csv(text: str) -> tuple[TreasuryAuctionedTipsRow, ...]:
    """Parse Treasury auctioned-security CSV rows and retain TIPS records only."""

    reader = csv.DictReader(StringIO(text.strip()))
    parsed_rows: list[TreasuryAuctionedTipsRow] = []
    for raw_row in reader:
        normalized = _normalize_row(raw_row)
        if not _is_tips_row(normalized):
            continue
        parsed_rows.append(_row_from_normalized_payload(normalized))
    return tuple(parsed_rows)


def load_treasury_auctioned_tips_json(path: str | Path) -> tuple[TreasuryAuctionedTipsRow, ...]:
    """Load Treasury auctioned-security TIPS rows from JSON on disk."""

    return parse_treasury_auctioned_tips_json(Path(path).read_text())


def load_treasury_auctioned_tips_csv(path: str | Path) -> tuple[TreasuryAuctionedTipsRow, ...]:
    """Load Treasury auctioned-security TIPS rows from CSV on disk."""

    return parse_treasury_auctioned_tips_csv(Path(path).read_text())


def tips_bond_from_treasury_auction_row(
    row: TreasuryAuctionedTipsRow,
    *,
    fixing_source: object | None = None,
    identifiers: object | None = None,
) -> TipsBond:
    """Convert a parsed Treasury TIPS row into a ``TipsBond``."""

    if row.dated_date is None:
        raise ValueError("Treasury TIPS row requires DatedDate to build TipsBond without guessing.")

    resolved_identifiers = identifiers
    if resolved_identifiers is None:
        preview = TipsBond.new(
            issue_date=row.issue_date,
            dated_date=row.dated_date,
            maturity_date=row.maturity_date,
            coupon_rate=row.coupon_rate / Decimal("100"),
            inflation_convention=USD_CPI_U_NSA,
            base_reference_date=row.dated_date,
            identifiers=None,
            fixing_source=fixing_source,
        )
        resolved_identifiers = replace(preview.identifiers(), cusip=row.cusip)

    return TipsBond.new(
        issue_date=row.issue_date,
        dated_date=row.dated_date,
        maturity_date=row.maturity_date,
        coupon_rate=row.coupon_rate / Decimal("100"),
        inflation_convention=USD_CPI_U_NSA,
        base_reference_date=row.dated_date,
        identifiers=resolved_identifiers,
        fixing_source=fixing_source,
    )


__all__ = [
    "InflationConvention",
    "InflationError",
    "InflationIndexDefinition",
    "InvalidObservationLag",
    "MissingInflationFixing",
    "TreasuryAuctionedTipsRow",
    "USD_CPI_U_NSA",
    "UnsupportedInflationInterpolation",
    "load_monthly_cpi_fixings_csv",
    "load_monthly_cpi_fixings_json",
    "load_treasury_auctioned_tips_csv",
    "load_treasury_auctioned_tips_json",
    "parse_bls_cpi_json",
    "parse_fred_cpi_csv",
    "parse_monthly_cpi_fixings_csv",
    "parse_monthly_cpi_fixings_json",
    "parse_treasury_auctioned_tips_csv",
    "parse_treasury_auctioned_tips_json",
    "reference_cpi",
    "reference_index_ratio",
    "tips_bond_from_treasury_auction_row",
    "treasury_cpi_source_from_fixings",
]
