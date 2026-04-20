"""Rates options product definitions."""

from __future__ import annotations

from importlib import import_module

_EXPORTS_BY_MODULE = (
    (
        "fuggers_py._products.instruments",
        ("HasExpiry", "HasOptionType", "HasUnderlyingInstrument"),
    ),
    (
        "fuggers_py._products.rates.options.cap_floor",
        ("CapFloor", "CapFloorType"),
    ),
    (
        "fuggers_py._products.rates.options.futures_option",
        ("FuturesOption",),
    ),
    (
        "fuggers_py._products.rates.options.swaption",
        ("Swaption",),
    ),
)


def _build_public_surface() -> tuple[list[str], dict[str, str]]:
    ordered_names: list[str] = []
    module_by_name: dict[str, str] = {}

    for module_name, export_names in _EXPORTS_BY_MODULE:
        for name in export_names:
            if name in module_by_name:
                continue
            ordered_names.append(name)
            module_by_name[name] = module_name

    return ordered_names, module_by_name


__all__, _MODULE_BY_NAME = _build_public_surface()


def __getattr__(name: str):
    module_name = _MODULE_BY_NAME.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(module_name), name)


def __dir__() -> list[str]:
    return sorted(__all__)
