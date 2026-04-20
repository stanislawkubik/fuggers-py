from __future__ import annotations

import json
from pathlib import Path


def _load_inventory() -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[3]
    inventory_path = repo_root / "refactor" / "PUBLIC_API_CURRENT_INVENTORY.json"
    return json.loads(inventory_path.read_text(encoding="utf-8"))


def test_current_inventory_freezes_the_current_phase1_owner_state() -> None:
    payload = _load_inventory()

    assert payload["schema_version"] == 1
    assert set(payload["canonical_public_packages"]) == {
        "fuggers_py",
        "fuggers_py.curves",
        "fuggers_py.vol_surfaces",
        "fuggers_py.bonds",
        "fuggers_py.rates",
        "fuggers_py.inflation",
        "fuggers_py.credit",
        "fuggers_py.funding",
        "fuggers_py.portfolio",
    }

    root_package = payload["canonical_public_packages"]["fuggers_py"]
    root_exports = {row["name"]: row for row in root_package["exports"]}
    assert root_package["facade"]["uses___getattr__"] is False
    assert root_package["facade"]["uses_import_module"] is False
    assert root_exports["Tenor"]["resolved_module"] == "fuggers_py._core.tenor"
    assert root_exports["CalendarId"]["resolved_module"] == "fuggers_py._core.calendar_id"
    assert root_exports["SettlementAdjustment"]["resolved_module"] == "fuggers_py._core.settlement_rules"
    assert root_exports["YieldCalculationRules"]["resolved_module"] == "fuggers_py._core.yield_calculation_rules"
    assert root_exports["BondType"]["resolved_module"] == "fuggers_py.bonds.types.bond_type"
    assert root_exports["IssuerType"]["resolved_module"] == "fuggers_py.bonds.types.issuer_type"
    assert root_exports["IndexConventions"]["resolved_module"] == "fuggers_py.rates.indices"

    curves_exports = {
        row["name"]: row for row in payload["canonical_public_packages"]["fuggers_py.curves"]["exports"]
    }
    assert curves_exports["YieldCurve"]["resolved_module"] == "fuggers_py.curves.base"

    legacy_paths = payload["legacy_public_import_paths"]
    assert legacy_paths["currently_importable"] == []
    assert "fuggers_py.market" in legacy_paths["retired_contract_paths"]
    assert "fuggers_py.products.bonds" in legacy_paths["retired_contract_paths"]

    market_modules = payload["drain_list_inventory"]["_market"]["modules"]
    overnight_module = next(
        module_row
        for module_row in market_modules
        if module_row["module"] == "fuggers_py._market.indices.overnight"
    )
    overnight_symbols = {row["name"] for row in overnight_module["public_symbols"]}
    assert "OvernightCompounding" in overnight_symbols

    reference_modules = payload["drain_list_inventory"]["_reference"]["modules"]
    moved_names = {
        "Tenor",
        "CalendarId",
        "SettlementAdjustment",
        "YieldCalculationRules",
        "BondType",
        "IssuerType",
    }
    assert [
        module_row["module"]
        for module_row in reference_modules
        if {row["name"] for row in module_row["public_symbols"]} & moved_names
    ] == []

    products_rates_modules = payload["drain_list_inventory"]["_products"]["modules"]
    common_module = next(
        module_row
        for module_row in products_rates_modules
        if module_row["module"] == "fuggers_py._products.rates.common"
    )
    common_symbols = {row["name"] for row in common_module["public_symbols"]}
    assert "PayReceive" not in common_symbols

    rates_module = next(
        module_row
        for module_row in products_rates_modules
        if module_row["module"] == "fuggers_py._products.rates"
    )
    rates_symbols = {row["name"] for row in rates_module["public_symbols"]}
    assert "PayReceive" not in rates_symbols
    assert "OptionType" not in rates_symbols

    options_module = next(
        module_row
        for module_row in products_rates_modules
        if module_row["module"] == "fuggers_py._products.rates.options"
    )
    options_symbols = {row["name"] for row in options_module["public_symbols"]}
    assert "OptionType" not in options_symbols

    options_common_module = next(
        module_row
        for module_row in products_rates_modules
        if module_row["module"] == "fuggers_py._products.rates.options._common"
    )
    options_common_symbols = {row["name"] for row in options_common_module["public_symbols"]}
    assert "OptionType" not in options_common_symbols
