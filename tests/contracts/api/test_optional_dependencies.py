from __future__ import annotations

import importlib

import pytest


def test_calc_namespace_is_no_longer_public_even_without_engine_extra() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("fuggers_py.calc")
