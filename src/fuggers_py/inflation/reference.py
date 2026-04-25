"""Reference CPI helpers and Treasury TIPS reference adapters."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, replace
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Any

import fuggers_py
from fuggers_py._core import YearMonth
from fuggers_py._core.types import Date

from .conventions import InflationConvention, InflationInterpolation, USD_CPI_U_NSA
from .errors import InvalidObservationLag, MissingInflationFixing, UnsupportedInflationInterpolation
from .history import InflationFixing, InflationFixingSourceLike


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
) -> fuggers_py.bonds.TipsBond:
    """Convert a parsed Treasury TIPS row into a ``TipsBond``."""

    from fuggers_py.bonds import TipsBond

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
    "MissingInflationFixing",
    "TreasuryAuctionedTipsRow",
    "UnsupportedInflationInterpolation",
    "load_treasury_auctioned_tips_csv",
    "load_treasury_auctioned_tips_json",
    "parse_treasury_auctioned_tips_csv",
    "parse_treasury_auctioned_tips_json",
    "reference_cpi",
    "reference_index_ratio",
    "tips_bond_from_treasury_auction_row",
]
