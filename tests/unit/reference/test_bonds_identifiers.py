from __future__ import annotations

import pytest

from fuggers_py.reference.bonds.errors import InvalidIdentifier
from fuggers_py.reference.bonds.types import Cusip, Figi, Isin, Sedol


def test_identifier_validation_valid_examples() -> None:
    assert str(Cusip.new("037833100")) == "037833100"
    assert str(Figi.new("BBG000BLNNH6")) == "BBG000BLNNH6"
    assert str(Sedol.new("2588173")) == "2588173"
    assert str(Isin.new("US0378331005")) == "US0378331005"


def test_identifier_validation_invalid_examples() -> None:
    with pytest.raises(InvalidIdentifier):
        _ = Cusip.new("037833101")  # wrong check digit
    with pytest.raises(InvalidIdentifier):
        _ = Cusip.new("097023AH0")  # wrong check digit

    with pytest.raises(InvalidIdentifier):
        _ = Figi.new("XXG000BLNNH6")  # wrong prefix

    with pytest.raises(InvalidIdentifier):
        _ = Sedol.new("258A173")  # vowel not allowed

    with pytest.raises(InvalidIdentifier):
        _ = Isin.new("120378331005")  # invalid country code format
    with pytest.raises(InvalidIdentifier):
        _ = Isin.new("US0378331004")  # wrong check digit
