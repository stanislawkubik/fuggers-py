"""Treasury auctioned-security adapters for TIPS instrument metadata.

The module parses Treasury auction feeds into a normalized TIPS row structure
and can then convert those rows into bond instruments.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, replace
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Any

from fuggers_py.products.bonds.instruments.tips import TipsBond
from fuggers_py.reference.bonds.types import BondIdentifiers, Cusip
from fuggers_py.core.types import Date

from .conventions import USD_CPI_U_NSA


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
    """Subset of Treasury auctioned-security TIPS metadata used by the library.

    ``coupon_rate`` stores the Treasury feed value as a percentage, for example
    ``Decimal("1.625")`` for a 1.625% coupon.
    """

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
        dated_date=(
            None
            if _optional_value(row, ("dateddate",)) is None
            else _parse_date(_optional_value(row, ("dateddate",)))
        ),
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
    identifiers: BondIdentifiers | None = None,
) -> TipsBond:
    """Convert a parsed Treasury TIPS row into a ``TipsBond``.

    When both ``issue_date`` and ``dated_date`` are present, ``dated_date`` is
    used for the bond's dated date and base reference date because it is the
    economically relevant anchor for reopened TIPS. Missing ``dated_date`` is
    treated as an error rather than guessed silently.
    """

    if row.dated_date is None:
        raise ValueError("Treasury TIPS row requires DatedDate to build TipsBond without guessing.")

    resolved_identifiers = identifiers or BondIdentifiers()
    if resolved_identifiers.cusip is None:
        resolved_identifiers = replace(resolved_identifiers, cusip=Cusip.new(row.cusip))

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
    "TreasuryAuctionedTipsRow",
    "load_treasury_auctioned_tips_csv",
    "load_treasury_auctioned_tips_json",
    "parse_treasury_auctioned_tips_csv",
    "parse_treasury_auctioned_tips_json",
    "tips_bond_from_treasury_auction_row",
]
