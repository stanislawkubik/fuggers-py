from __future__ import annotations

import importlib

import pytest


def test_legacy_adapters_package_is_absent() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("fuggers_py._adapters")


def test_storage_error_module_is_not_part_of_the_surface() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("fuggers_py._storage.errors")
