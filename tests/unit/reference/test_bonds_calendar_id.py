from __future__ import annotations

import pytest

from fuggers_py.reference.bonds.errors import InvalidIdentifier
from fuggers_py.reference.bonds.types import CalendarId


def test_calendar_id_canonical_strings_and_mapping() -> None:
    assert CalendarId.us_government().as_str() == "USGov"
    assert CalendarId.weekend_only().as_str() == "WEEKEND"

    assert CalendarId.us_government().to_calendar().name() == "USGovernment"
    assert CalendarId.sifma().to_calendar().name() == "SIFMA"
    assert CalendarId.uk().to_calendar().name() == "UK"
    assert CalendarId.target2().to_calendar().name() == "TARGET2"
    assert CalendarId.japan().to_calendar().name() == "Japan"


def test_calendar_id_legacy_strings_still_map() -> None:
    assert CalendarId.new("US_GOVERNMENT").to_calendar().name() == "USGovernment"
    assert CalendarId.new("WEEKEND_ONLY").to_calendar().name() == "WeekendCalendar"


def test_calendar_id_empty_rejected() -> None:
    with pytest.raises(InvalidIdentifier):
        _ = CalendarId.new("")

