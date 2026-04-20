from __future__ import annotations

import importlib

import pytest


def test_math_namespace_is_not_public_anymore() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("fuggers_py.math")
