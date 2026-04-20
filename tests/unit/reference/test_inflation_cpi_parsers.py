from __future__ import annotations

import json
from decimal import Decimal

import pytest

from fuggers_py._core import YearMonth
from fuggers_py.inflation import (
    load_monthly_cpi_fixings_csv,
    parse_bls_cpi_json,
    parse_fred_cpi_csv,
    parse_monthly_cpi_fixings_csv,
    parse_monthly_cpi_fixings_json,
)


def test_parse_monthly_cpi_fixings_csv_and_json_preserve_cpurnsa() -> None:
    csv_fixings = parse_monthly_cpi_fixings_csv(
        "\n".join(
            [
                "observation_month,cpi",
                "2024-01,308.417",
                "2024-02,310.326",
            ]
        )
    )
    json_fixings = parse_monthly_cpi_fixings_json(
        {
            "data": [
                {"month": "2024-01", "reference_cpi": "308.417"},
                {"month": "2024-02", "reference_cpi": "310.326"},
            ]
        }
    )

    assert csv_fixings == json_fixings
    assert csv_fixings[0].index_name == "CPURNSA"


def test_load_monthly_cpi_fixings_csv_reads_fixture_from_disk(tmp_path) -> None:
    path = tmp_path / "monthly_cpi.csv"
    path.write_text("observation_month,cpi\n2024-01,308.417\n")

    fixings = load_monthly_cpi_fixings_csv(path)

    assert len(fixings) == 1
    assert fixings[0].observation_month == YearMonth(2024, 1)


def test_parse_bls_cpi_json_skips_annual_average_and_preserves_index_name() -> None:
    payload = json.dumps(
        {
            "Results": {
                "series": [
                    {
                        "seriesID": "CUUR0000SA0",
                        "data": [
                            {"year": "2024", "period": "M02", "value": "310.326"},
                            {"year": "2024", "period": "M01", "value": "308.417"},
                            {"year": "2024", "period": "M13", "value": "309.000"},
                        ],
                    }
                ]
            }
        }
    )

    fixings = parse_bls_cpi_json(payload)

    assert [fixing.observation_month for fixing in fixings] == [YearMonth(2024, 2), YearMonth(2024, 1)]
    assert all(fixing.index_name == "CPURNSA" for fixing in fixings)
    assert fixings[0].value == Decimal("310.326")


def test_parse_fred_cpi_csv_parses_standard_export_shape() -> None:
    text = "\n".join(
        [
            "DATE,CPIAUCNS",
            "2024-01-01,308.417",
            "2024-02-01,310.326",
        ]
    )

    fixings = parse_fred_cpi_csv(text)

    assert [fixing.observation_month for fixing in fixings] == [YearMonth(2024, 1), YearMonth(2024, 2)]
    assert all(fixing.index_name == "CPURNSA" for fixing in fixings)


def test_parse_monthly_cpi_fixings_raises_clear_error_when_value_is_missing() -> None:
    with pytest.raises(ValueError, match="value/cpi/reference_cpi/index_level"):
        parse_monthly_cpi_fixings_json({"data": [{"month": "2024-01"}]})


def test_parse_bls_cpi_json_rejects_non_monthly_periods() -> None:
    payload = {
        "Results": {
            "series": [
                {
                    "seriesID": "CUUR0000SA0",
                    "data": [{"year": "2024", "period": "Q01", "value": "308.417"}],
                }
            ]
        }
    }

    with pytest.raises(ValueError, match="M01-M12"):
        parse_bls_cpi_json(payload)
