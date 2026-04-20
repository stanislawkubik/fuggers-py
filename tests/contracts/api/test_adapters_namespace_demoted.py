from __future__ import annotations

import importlib

import pytest


def test_adapters_namespace_is_no_longer_public() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("fuggers_py.adapters")
