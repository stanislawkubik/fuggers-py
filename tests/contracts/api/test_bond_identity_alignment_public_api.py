from __future__ import annotations

import pytest

import fuggers_py.products.bonds as products_bonds
import fuggers_py.products.bonds.instruments as bond_instruments
from fuggers_py.products.bonds import (
    CallableBond,
    CallableBondBuilder,
    FixedBond,
    FixedBondBuilder,
    FloatingRateNote,
    FloatingRateNoteBuilder,
    SinkingFundBond,
    SinkingFundBondBuilder,
    TipsBond,
    ZeroCouponBond,
)
from fuggers_py.products.instruments import Instrument


@pytest.mark.feature_slug("bond-identity-alignment")
@pytest.mark.feature_category("api_contract")
def test_bond_root_imports_remain_stable_while_identity_surface_expands() -> None:
    assert FixedBond is bond_instruments.FixedBond
    assert ZeroCouponBond is bond_instruments.ZeroCouponBond
    assert FloatingRateNote is bond_instruments.FloatingRateNote
    assert TipsBond is bond_instruments.TipsBond
    assert SinkingFundBond is bond_instruments.SinkingFundBond
    assert CallableBond is bond_instruments.CallableBond
    assert FixedBondBuilder is bond_instruments.FixedBondBuilder
    assert FloatingRateNoteBuilder is bond_instruments.FloatingRateNoteBuilder
    assert SinkingFundBondBuilder is bond_instruments.SinkingFundBondBuilder
    assert CallableBondBuilder is bond_instruments.CallableBondBuilder
    assert products_bonds.FixedBondBuilder is FixedBondBuilder
    assert Instrument.__name__ == "Instrument"


@pytest.mark.feature_slug("bond-identity-alignment")
@pytest.mark.feature_category("api_contract")
def test_bond_builders_expose_public_instrument_id_setters() -> None:
    assert hasattr(FixedBondBuilder.new(), "with_instrument_id")
    assert hasattr(FloatingRateNoteBuilder.new(), "with_instrument_id")
    assert hasattr(SinkingFundBondBuilder.new(), "with_instrument_id")
