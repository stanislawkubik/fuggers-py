from __future__ import annotations

import importlib

import pytest

import fuggers_py.bonds as bonds_pkg
from fuggers_py.bonds import (
    ASWType,
    DiscountMarginCalculator,
    OASCalculator,
    ParParAssetSwap,
    ProceedsAssetSwap,
    g_spread,
    i_spread,
    z_spread,
)


def test_top_level_spreads_namespace_is_removed() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("fuggers_py.spreads")


def test_bonds_namespace_reexports_the_public_spread_surface() -> None:
    assert bonds_pkg.ASWType is ASWType
    assert bonds_pkg.g_spread is g_spread
    assert bonds_pkg.i_spread is i_spread
    assert bonds_pkg.z_spread is z_spread
    assert bonds_pkg.OASCalculator is OASCalculator
    assert bonds_pkg.DiscountMarginCalculator is DiscountMarginCalculator
    assert bonds_pkg.ParParAssetSwap is ParParAssetSwap
    assert bonds_pkg.ProceedsAssetSwap is ProceedsAssetSwap
