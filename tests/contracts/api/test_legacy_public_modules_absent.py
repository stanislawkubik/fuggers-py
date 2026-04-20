from __future__ import annotations

import importlib

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "fuggers_py.market",
        "fuggers_py.market.snapshot",
        "fuggers_py.market.state",
        "fuggers_py.market.sources",
        "fuggers_py.market.quotes",
        "fuggers_py.market.curves",
        "fuggers_py.market.vol_surfaces",
        "fuggers_py.products",
        "fuggers_py.products.bonds",
        "fuggers_py.pricers",
        "fuggers_py.pricers.bonds",
        "fuggers_py.measures",
        "fuggers_py.measures.functions",
        "fuggers_py.reference",
        "fuggers_py.reference.bonds.types",
        "fuggers_py.calc",
        "fuggers_py.calc.scheduler",
        "fuggers_py.core",
        "fuggers_py.core.errors",
        "fuggers_py.adapters",
        "fuggers_py.adapters.file",
        "fuggers_py.math",
        "fuggers_py.math.solvers",
        "fuggers_py.fixings",
        "fuggers_py.derivatives",
        "fuggers_py.market.fixings",
        "fuggers_py.market.derivatives",
        "fuggers_py.market.curves.fitted_bonds",
        "fuggers_py.market.curves.inflation",
    ],
)
def test_non_target_public_modules_are_not_importable(module_name: str) -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)
