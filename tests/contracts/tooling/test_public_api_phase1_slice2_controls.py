from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_validator():
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "tools" / "validate_public_api_refactor.py"
    spec = importlib.util.spec_from_file_location("validate_public_api_refactor_module_slice2", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_phase1_slice2_control_files_match_the_generator() -> None:
    module = _load_validator()
    repo_root = Path(__file__).resolve().parents[3]

    expected_manifest = json.loads((repo_root / "refactor" / "PUBLIC_API_EXPORT_MANIFEST.json").read_text(encoding="utf-8"))
    expected_denylist = json.loads((repo_root / "refactor" / "PUBLIC_API_LEGACY_DENYLIST.json").read_text(encoding="utf-8"))
    expected_ledger = json.loads((repo_root / "refactor" / "PUBLIC_API_MIGRATION_LEDGER.json").read_text(encoding="utf-8"))

    assert module.build_public_api_export_manifest(repo_root) == expected_manifest
    assert module.build_public_api_legacy_denylist(repo_root) == expected_denylist
    assert module.build_public_api_migration_ledger(repo_root) == expected_ledger


def test_phase1_slice2_control_files_capture_key_owner_decisions() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    manifest = json.loads((repo_root / "refactor" / "PUBLIC_API_EXPORT_MANIFEST.json").read_text(encoding="utf-8"))
    denylist = json.loads((repo_root / "refactor" / "PUBLIC_API_LEGACY_DENYLIST.json").read_text(encoding="utf-8"))
    ledger = json.loads((repo_root / "refactor" / "PUBLIC_API_MIGRATION_LEDGER.json").read_text(encoding="utf-8"))

    root_exports = {row["name"]: row for row in manifest["packages"]["fuggers_py"]["exports"]}
    assert root_exports["Tenor"]["owning_package"] == "fuggers_py._core"
    assert root_exports["BondType"]["owning_package"] == "fuggers_py.bonds"
    assert root_exports["IndexConventions"]["owning_package"] == "fuggers_py.rates"

    denylist_entries = {row["legacy_import_path"]: row for row in denylist["entries"]}
    assert denylist_entries["fuggers_py.market.curves"]["replacement_import_path"] == "fuggers_py.curves"
    assert denylist_entries["fuggers_py.market.snapshot"]["replacement_import_path"] is None

    ledger_entries = {row["entry_id"]: row for row in ledger["entries"]}
    assert ledger_entries["public:fuggers_py:Tenor"]["decision"] == "move to fuggers_py._core"
    assert (
        ledger_entries["drain:fuggers_py._market.indices.overnight:OvernightCompounding"]["decision"]
        == "internalize under fuggers_py.rates"
    )
    assert ledger_entries["drain:fuggers_py._market.indices:IndexConventions"]["decision"] == "delete"
