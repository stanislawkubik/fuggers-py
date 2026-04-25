from __future__ import annotations

import importlib
import inspect
import json
from typing import get_type_hints

from tests.helpers._paths import REPO_ROOT


SURFACE_PATH = REPO_ROOT / "specs" / "public_api_surface.json"


def test_public_class_and_function_type_hints_resolve() -> None:
    surface = json.loads(SURFACE_PATH.read_text(encoding="utf-8"))
    failures: list[str] = []

    for package_name, payload in surface["modules"].items():
        module = importlib.import_module(package_name)
        for name in payload["exports"]:
            exported = getattr(module, name)
            if not (inspect.isclass(exported) or inspect.isfunction(exported)):
                continue
            try:
                get_type_hints(exported)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{package_name}.{name}: {type(exc).__name__}: {exc}")

    assert failures == []
