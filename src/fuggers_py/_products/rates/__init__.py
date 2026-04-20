"""Internal rates product definitions."""

from __future__ import annotations

from importlib import import_module

_EXPORTS_BY_MODULE = (
    (
        "fuggers_py._products.rates.asset_swap",
        ("AssetSwap",),
    ),
    (
        "fuggers_py._products.rates.basis_swap",
        ("BasisSwap", "SameCurrencyBasisSwap"),
    ),
    (
        "fuggers_py._products.rates.common",
        (
            "AccrualPeriod",
            "FixedLegSpec",
            "FloatingLegSpec",
            "ScheduleDefinition",
        ),
    ),
    (
        "fuggers_py._products.rates.cross_currency_basis",
        ("CrossCurrencyBasisSwap",),
    ),
    (
        "fuggers_py._products.rates.fixed_float_swap",
        ("FixedFloatSwap", "InterestRateSwap"),
    ),
    (
        "fuggers_py._products.rates.fra",
        ("ForwardRateAgreement", "Fra"),
    ),
    (
        "fuggers_py._products.rates.futures",
        ("DeliverableBasket", "DeliverableBond", "GovernmentBondFuture"),
    ),
    (
        "fuggers_py._products.rates.options",
        (
            "CapFloor",
            "CapFloorType",
            "FuturesOption",
            "Swaption",
        ),
    ),
    (
        "fuggers_py._products.rates.ois",
        ("Ois", "OvernightIndexedSwap"),
    ),
    (
        "fuggers_py._products.instruments",
        ("HasExpiry", "HasOptionType", "HasUnderlyingInstrument"),
    ),
)
_PACKAGE_EXPORTS = {
    "futures": "fuggers_py._products.rates.futures",
    "options": "fuggers_py._products.rates.options",
}


def _build_public_surface() -> tuple[list[str], dict[str, str]]:
    ordered_names: list[str] = list(_PACKAGE_EXPORTS)
    module_by_name: dict[str, str] = dict(_PACKAGE_EXPORTS)

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
    module = import_module(module_name)
    if name in _PACKAGE_EXPORTS:
        return module
    return getattr(module, name)


def __dir__() -> list[str]:
    return sorted(__all__)
