from __future__ import annotations

import json
from decimal import Decimal

import pytest

from fuggers_py.core import Date
from fuggers_py.reference.inflation import (
    TreasuryAuctionedTipsRow,
    parse_treasury_auctioned_tips_csv,
    parse_treasury_auctioned_tips_json,
    tips_bond_from_treasury_auction_row,
)


def _auctioned_tips_fixture() -> dict[str, object]:
    return {
        "CUSIP": "912810UH9",
        "SecurityType": "Bond",
        "SecurityTerm": "29-Year 6-Month",
        "SecurityTermWeekYear": "29-Year 6-Month TIPS of February 2055",
        "IssueDate": "2025-08-29T00:00:00",
        "DatedDate": "2025-08-15T00:00:00",
        "MaturityDate": "2055-02-15T00:00:00",
        "InterestRate": "2.375000",
        "OriginalIssueDate": "2025-02-15T00:00:00",
        "RefCpiOnIssueDate": "322.454940",
        "RefCpiOnDatedDate": "315.549000",
        "OriginalSecurityTerm": "30-Year",
        "ExtraColumn": "ignored",
    }


def test_parse_treasury_auctioned_tips_json_filters_non_tips_rows() -> None:
    payload = json.dumps(
        {
            "data": [
                {
                    "CUSIP": "91282CMM9",
                    "SecurityType": "Note",
                    "SecurityTerm": "10-Year",
                    "IssueDate": "2025-08-15T00:00:00",
                    "MaturityDate": "2035-08-15T00:00:00",
                    "InterestRate": "4.125000",
                },
                _auctioned_tips_fixture(),
            ]
        }
    )

    rows = parse_treasury_auctioned_tips_json(payload)

    assert rows == (
        TreasuryAuctionedTipsRow(
            cusip="912810UH9",
            security_type="Bond",
            security_term="29-Year 6-Month",
            issue_date=Date.from_ymd(2025, 8, 29),
            dated_date=Date.from_ymd(2025, 8, 15),
            maturity_date=Date.from_ymd(2055, 2, 15),
            coupon_rate=Decimal("2.375000"),
            original_issue_date=Date.from_ymd(2025, 2, 15),
            ref_cpi_on_issue_date=Decimal("322.454940"),
            ref_cpi_on_dated_date=Decimal("315.549000"),
            original_security_term="30-Year",
        ),
    )


def test_parse_treasury_auctioned_tips_csv_parses_minimal_fixture() -> None:
    text = "\n".join(
        [
            "CUSIP,SecurityType,SecurityTerm,SecurityTermWeekYear,IssueDate,DatedDate,MaturityDate,InterestRate,RefCpiOnIssueDate",
            "91282CMM9,Note,10-Year,10-Year Note of August 2035,2025-08-15T00:00:00,,2035-08-15T00:00:00,4.125000,",
            "912810UH9,Bond,29-Year 6-Month,29-Year 6-Month TIPS of February 2055,2025-08-29T00:00:00,2025-08-15T00:00:00,2055-02-15T00:00:00,2.375000,322.454940",
        ]
    )

    rows = parse_treasury_auctioned_tips_csv(text)

    assert len(rows) == 1
    assert rows[0].cusip == "912810UH9"
    assert rows[0].dated_date == Date.from_ymd(2025, 8, 15)
    assert rows[0].coupon_rate == Decimal("2.375000")


def test_tips_bond_from_treasury_auction_row_preserves_cusip_and_dates() -> None:
    row = parse_treasury_auctioned_tips_json({"data": [_auctioned_tips_fixture()]})[0]

    bond = tips_bond_from_treasury_auction_row(row)

    assert bond.issue_date() == Date.from_ymd(2025, 8, 29)
    assert bond.dated_date() == Date.from_ymd(2025, 8, 15)
    assert bond.base_reference_date() == Date.from_ymd(2025, 8, 15)
    assert bond.maturity_date() == Date.from_ymd(2055, 2, 15)
    assert bond.coupon_rate() == Decimal("0.02375")
    assert bond.inflation_convention().index_source == "CPURNSA"
    assert bond.identifiers().cusip is not None
    assert str(bond.identifiers().cusip) == "912810UH9"


def test_treasury_auctioned_tips_parser_raises_for_missing_required_fields() -> None:
    payload = {
        "data": [
            {
                "CUSIP": "912810UH9",
                "SecurityType": "Bond",
                "SecurityTermWeekYear": "29-Year 6-Month TIPS of February 2055",
                "IssueDate": "2025-08-29T00:00:00",
                "InterestRate": "2.375000",
            }
        ]
    }

    with pytest.raises(ValueError, match="MaturityDate"):
        parse_treasury_auctioned_tips_json(payload)


def test_tips_bond_from_treasury_auction_row_requires_dated_date() -> None:
    row = TreasuryAuctionedTipsRow(
        cusip="912810UH9",
        security_type="Bond",
        security_term="10-Year",
        issue_date=Date.from_ymd(2025, 7, 31),
        dated_date=None,
        maturity_date=Date.from_ymd(2035, 7, 15),
        coupon_rate=Decimal("1.625000"),
    )

    with pytest.raises(ValueError, match="DatedDate"):
        tips_bond_from_treasury_auction_row(row)
