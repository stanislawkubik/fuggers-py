from __future__ import annotations

from decimal import Decimal

from fuggers_py.credit import bond_cds_basis, bond_cds_basis_breakdown


def test_bond_cds_basis_uses_adjusted_cds_spread_and_explicit_sign_convention() -> None:
    breakdown = bond_cds_basis_breakdown(
        bond_spread=Decimal("0.0180"),
        cds_spread=Decimal("0.0150"),
        delivery_option_adjustment=Decimal("0.0010"),
        fx_adjustment=Decimal("0.0005"),
    )

    assert breakdown.adjusted_cds_spread == Decimal("0.0135")
    assert breakdown.basis == Decimal("0.0045")
    assert bond_cds_basis(
        bond_spread=Decimal("0.0180"),
        cds_spread=Decimal("0.0150"),
        delivery_option_adjustment=Decimal("0.0010"),
        fx_adjustment=Decimal("0.0005"),
    ) == Decimal("0.0045")


def test_bond_cds_basis_is_negative_when_cash_bond_is_rich_to_cds() -> None:
    assert bond_cds_basis(
        bond_spread=Decimal("0.0100"),
        cds_spread=Decimal("0.0120"),
    ) == Decimal("-0.0020")
