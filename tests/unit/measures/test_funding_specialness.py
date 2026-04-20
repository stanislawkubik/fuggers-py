from __future__ import annotations

from decimal import Decimal

from fuggers_py.funding import is_special, specialness_spread, specialness_value


def test_specialness_helpers_use_explicit_positive_for_special_sign_convention() -> None:
    spread = specialness_spread(
        general_collateral_rate=Decimal("0.04"),
        specific_collateral_rate=Decimal("0.035"),
    )

    assert spread == Decimal("0.005")
    assert is_special(general_collateral_rate=Decimal("0.04"), specific_collateral_rate=Decimal("0.035")) is True
    assert is_special(general_collateral_rate=Decimal("0.04"), specific_collateral_rate=Decimal("0.045")) is False
    assert specialness_value(
        cash_amount=Decimal("1000000"),
        general_collateral_rate=Decimal("0.04"),
        specific_collateral_rate=Decimal("0.035"),
        year_fraction=Decimal("0.25"),
    ) == Decimal("1250.00000")
