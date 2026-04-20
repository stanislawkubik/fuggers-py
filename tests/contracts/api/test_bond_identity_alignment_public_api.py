from __future__ import annotations

import pytest

import fuggers_py.bonds as bonds_pkg
from fuggers_py.bonds import (
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


@pytest.mark.feature_slug("bond-identity-alignment")
@pytest.mark.feature_category("api_contract")
def test_bond_root_imports_are_the_stable_public_identity_surface() -> None:
    assert bonds_pkg.FixedBond is FixedBond
    assert bonds_pkg.ZeroCouponBond is ZeroCouponBond
    assert bonds_pkg.FloatingRateNote is FloatingRateNote
    assert bonds_pkg.TipsBond is TipsBond
    assert bonds_pkg.SinkingFundBond is SinkingFundBond
    assert bonds_pkg.CallableBond is CallableBond
    assert bonds_pkg.FixedBondBuilder is FixedBondBuilder
    assert bonds_pkg.FloatingRateNoteBuilder is FloatingRateNoteBuilder
    assert bonds_pkg.SinkingFundBondBuilder is SinkingFundBondBuilder
    assert bonds_pkg.CallableBondBuilder is CallableBondBuilder


@pytest.mark.feature_slug("bond-identity-alignment")
@pytest.mark.feature_category("api_contract")
def test_bond_builders_expose_public_instrument_id_setters() -> None:
    assert hasattr(FixedBondBuilder.new(), "with_instrument_id")
    assert hasattr(FloatingRateNoteBuilder.new(), "with_instrument_id")
    assert hasattr(SinkingFundBondBuilder.new(), "with_instrument_id")
