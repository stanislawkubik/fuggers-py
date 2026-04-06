from __future__ import annotations

import importlib

import pytest


def test_top_level_spreads_namespace_is_removed() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("fuggers_py.spreads")


def test_analytics_spreads_namespace_is_canonical() -> None:
    module = importlib.import_module("fuggers_py.measures.spreads")

    assert module.ASWType is not None
    assert module.g_spread is not None
    assert module.i_spread is not None
    assert module.z_spread is not None
    assert module.OASCalculator is not None
    assert module.DiscountMarginCalculator is not None
    assert module.ParParAssetSwap is not None
    assert module.ProceedsAssetSwap is not None
