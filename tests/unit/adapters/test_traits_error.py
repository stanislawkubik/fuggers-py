from __future__ import annotations

import importlib

import pytest

import fuggers_py._adapters as adapters


def test_adapter_root_does_not_export_unused_generic_error_types() -> None:
    assert not hasattr(adapters, "TraitError")
    assert not hasattr(adapters, "ConnectionFailureError")
    assert not hasattr(adapters, "PermissionDeniedError")


def test_adapter_error_module_is_not_part_of_the_public_surface() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("fuggers_py._adapters.errors")
