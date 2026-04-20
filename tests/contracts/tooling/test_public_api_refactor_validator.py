from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import tomllib
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType

import pytest


def _load_validator() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "tools" / "validate_public_api_refactor.py"
    spec = importlib.util.spec_from_file_location("validate_public_api_refactor_module", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _purge_loaded_fuggers_py_modules() -> None:
    original_sys_path = list(sys.path)
    original_modules = {
        module_name: module
        for module_name, module in sys.modules.items()
        if module_name == "fuggers_py" or module_name.startswith("fuggers_py.")
    }
    yield
    sys.path[:] = original_sys_path
    for module_name in list(sys.modules):
        if module_name == "fuggers_py" or module_name.startswith("fuggers_py."):
            del sys.modules[module_name]
    sys.modules.update(original_modules)


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "tests@example.com"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Tests"], cwd=root, check=True, capture_output=True, text=True)


def _git_commit_all(root: Path, message: str) -> None:
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", message], cwd=root, check=True, capture_output=True, text=True)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_minimal_control_files(root: Path) -> None:
    _write_text(
        root / "refactor" / "PUBLIC_API_CURRENT_INVENTORY.json",
        json.dumps(
            {
                "schema_version": 1,
                "canonical_public_packages": {},
                "legacy_public_import_paths": {},
                "drain_list_inventory": {},
            }
        )
        + "\n",
    )
    _write_text(
        root / "refactor" / "PUBLIC_API_EXPORT_MANIFEST.json",
        json.dumps({"schema_version": 1, "packages": {}}) + "\n",
    )
    _write_text(
        root / "refactor" / "PUBLIC_API_LEGACY_DENYLIST.json",
        json.dumps({"schema_version": 1, "entries": []}) + "\n",
    )
    _write_text(
        root / "refactor" / "PUBLIC_API_MIGRATION_LEDGER.json",
        json.dumps({"schema_version": 1, "entries": []}) + "\n",
    )
    _write_text(
        root / "refactor" / "PUBLIC_API_STRUCTURE_MANIFEST.json",
        json.dumps(
            {
                "schema_version": 1,
                "phase": "phase1_slice3",
                "root_package": "fuggers_py",
                "top_level_packages": {},
                "canonical_public_package_trees": {},
            }
        )
        + "\n",
    )
    _write_text(
        root / "refactor" / "PUBLIC_API_DEPENDENCY_MANIFEST.json",
        json.dumps({"schema_version": 1, "packages": {}}) + "\n",
    )


def _write_minimal_slice3_prerequisites(root: Path) -> None:
    _write_text(root / "refactor" / "PUBLIC_API_TARGET_STATE.md", "# target\n")
    _write_text(root / "refactor" / "PUBLIC_API_REFACTOR_PLAN.md", "# plan\n")
    _write_text(root / "src" / "fuggers_py" / "__init__.py", "__all__ = []\n")

    for package_name in [
        "_core",
        "_math",
        "_runtime",
        "_storage",
        "_products",
        "curves",
        "vol_surfaces",
        "bonds",
        "rates",
        "inflation",
        "credit",
        "funding",
        "portfolio",
    ]:
        _write_text(root / "src" / "fuggers_py" / package_name / "__init__.py", "__all__ = []\n")

    _write_text(
        root / "refactor" / "PUBLIC_API_CURRENT_INVENTORY.json",
        json.dumps(
            {
                "schema_version": 1,
                "canonical_public_packages": {},
                "legacy_public_import_paths": {},
                "drain_list_inventory": {},
            }
        )
        + "\n",
    )
    _write_text(
        root / "refactor" / "PUBLIC_API_EXPORT_MANIFEST.json",
        json.dumps(
            {
                "schema_version": 1,
                "packages": {
                    "fuggers_py": {
                        "exports": [
                            {"name": "curves", "kind": "module", "owning_package": "fuggers_py.curves"},
                            {"name": "Date", "kind": "class", "owning_package": "fuggers_py._core"},
                        ]
                    },
                    "fuggers_py.curves": {"exports": []},
                    "fuggers_py.vol_surfaces": {"exports": []},
                    "fuggers_py.bonds": {"exports": []},
                    "fuggers_py.rates": {"exports": []},
                    "fuggers_py.inflation": {"exports": []},
                    "fuggers_py.credit": {"exports": []},
                    "fuggers_py.funding": {"exports": []},
                    "fuggers_py.portfolio": {"exports": []},
                },
            }
        )
        + "\n",
    )
    _write_text(root / "refactor" / "PUBLIC_API_LEGACY_DENYLIST.json", json.dumps({"schema_version": 1, "entries": []}) + "\n")
    _write_text(root / "refactor" / "PUBLIC_API_MIGRATION_LEDGER.json", json.dumps({"schema_version": 1, "entries": []}) + "\n")


def _freeze_minimal_slice3_baseline(root: Path, module: ModuleType) -> None:
    _write_minimal_slice3_prerequisites(root)
    module.freeze_public_api_structure_controls(root)
    _git_commit_all(root, "freeze controls")
    module.init_workflow(root)


def test_init_workflow_uses_current_dirty_tree_as_baseline(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _git_commit_all(tmp_path, "base")
    _write_text(tmp_path / "docs" / "draft.md", "pending\n")

    state = module.init_workflow(tmp_path)

    assert state["workflow_name"] == "public-api-refactor"
    assert state["active"] is True
    assert state["baseline_changed_paths"] == ["docs/draft.md"]


def test_validate_rejects_deep_public_import_in_changed_user_facing_file(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _git_commit_all(tmp_path, "base")
    _freeze_minimal_slice3_baseline(tmp_path, module)

    _write_text(tmp_path / "docs" / "guide.py", "from fuggers_py.curves.internal import Thing\n")

    result = module.validate_workflow(tmp_path, run_commands=False)

    assert result.ok is False
    assert result.reason == (
        "docs/guide.py uses deep public import `fuggers_py.curves.internal`. "
        "Use one-layer imports from `fuggers_py.curves` instead."
    )


def test_validate_rejects_changed_legacy_public_entrypoint_wrapper_in_hard_rewrite(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _git_commit_all(tmp_path, "base")
    _freeze_minimal_slice3_baseline(tmp_path, module)

    _write_text(tmp_path / "src" / "fuggers_py" / "bonds" / "__init__.py", "__all__ = []\n")
    _write_text(
        tmp_path / "src" / "fuggers_py" / "products" / "bonds" / "__init__.py",
        "from fuggers_py.bonds import FixedBondBuilder\n",
    )

    result = module.validate_workflow(tmp_path, run_commands=False)

    assert result.ok is False
    assert result.reason == (
        "src/fuggers_py/products/bonds/__init__.py preserves the old public path by re-exporting `fuggers_py.bonds`. "
        "This refactor is a hard rewrite. Remove the legacy public entrypoint instead of wrapping the new module."
    )


def test_validate_rejects_thick_legacy_wrapper_with_logic(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _git_commit_all(tmp_path, "base")
    _freeze_minimal_slice3_baseline(tmp_path, module)

    _write_text(tmp_path / "src" / "fuggers_py" / "curves" / "__init__.py", "__all__ = []\n")
    _write_text(
        tmp_path / "src" / "fuggers_py" / "market" / "bridge.py",
        "\n".join(
            [
                "from fuggers_py.curves import YieldCurve",
                "",
                "def helper() -> str:",
                "    return YieldCurve.__name__",
                "",
            ]
        )
        + "\n",
    )

    result = module.validate_workflow(tmp_path, run_commands=False)

    assert result.ok is False
    assert result.reason == (
        "src/fuggers_py/market/bridge.py keeps compatibility logic in a legacy namespace: helper. "
        "This refactor is a hard rewrite. Move the logic to the new public module and delete the old public path."
    )


def test_validate_rejects_duplicate_symbols_left_in_legacy_location_even_if_old_file_is_untouched(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _write_minimal_slice3_prerequisites(tmp_path)
    _write_text(
        tmp_path / "src" / "fuggers_py" / "products" / "bonds" / "instruments.py",
        "\n".join(
            [
                "class FixedBond:",
                "    pass",
                "",
            ]
        ),
    )
    _git_commit_all(tmp_path, "base")
    module.freeze_public_api_structure_controls(tmp_path)
    _git_commit_all(tmp_path, "freeze controls")
    module.init_workflow(tmp_path)

    _write_text(
        tmp_path / "src" / "fuggers_py" / "bonds" / "instruments.py",
        "\n".join(
            [
                "class FixedBond:",
                "    pass",
                "",
            ]
        ),
    )

    result = module.validate_workflow(tmp_path, run_commands=False)

    assert result.ok is False
    assert result.reason == (
        "src/fuggers_py/products/bonds/instruments.py still defines moved symbols that now also exist under "
        "`fuggers_py.bonds`: FixedBond. This refactor is a hard rewrite. Remove the old implementation."
    )


def test_validate_rejects_canonical_public_absolute_import_from_drain_bucket(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _write_minimal_slice3_prerequisites(tmp_path)
    _git_commit_all(tmp_path, "base")
    module.freeze_public_api_structure_controls(tmp_path)
    _git_commit_all(tmp_path, "freeze controls")
    module.init_workflow(tmp_path)

    _write_text(
        tmp_path / "src" / "fuggers_py" / "bonds" / "products.py",
        "\n".join(
            [
                "from fuggers_py._products.bonds.instruments import FixedBond",
                "",
                "__all__ = []",
                "",
            ]
        ),
    )

    result = module.validate_workflow(tmp_path, run_commands=False)

    assert result.ok is False
    assert result.reason == (
        "src/fuggers_py/bonds/products.py imports forbidden drain bucket module "
        "`fuggers_py._products.bonds.instruments`. Canonical public packages must own live code under the public tree "
        "instead of importing drain-list buckets."
    )


def test_validate_rejects_canonical_public_relative_import_from_drain_bucket(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _write_minimal_slice3_prerequisites(tmp_path)
    _git_commit_all(tmp_path, "base")
    module.freeze_public_api_structure_controls(tmp_path)
    _git_commit_all(tmp_path, "freeze controls")
    module.init_workflow(tmp_path)

    _write_text(
        tmp_path / "src" / "fuggers_py" / "rates" / "indices.py",
        "\n".join(
            [
                "from .._market.indices.conventions import IndexConventions",
                "",
                "__all__ = []",
                "",
            ]
        ),
    )

    result = module.validate_workflow(tmp_path, run_commands=False)

    assert result.ok is False
    assert result.reason == (
        "src/fuggers_py/rates/indices.py imports forbidden drain bucket module "
        "`fuggers_py._market.indices.conventions`. Canonical public packages must own live code under the public tree "
        "instead of importing drain-list buckets."
    )


def test_validate_rejects_canonical_export_that_still_resolves_outside_declared_owner(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _write_minimal_slice3_prerequisites(tmp_path)
    _write_text(
        tmp_path / "src" / "fuggers_py" / "shared_curve_impl.py",
        "\n".join(
            [
                "class YieldCurve:",
                "    pass",
                "",
            ]
        ),
    )
    _write_text(
        tmp_path / "src" / "fuggers_py" / "curves" / "__init__.py",
        "\n".join(
            [
                "from fuggers_py.shared_curve_impl import YieldCurve",
                "",
                '__all__ = ["YieldCurve"]',
                "",
            ]
        ),
    )
    _write_text(
        tmp_path / "refactor" / "PUBLIC_API_EXPORT_MANIFEST.json",
        json.dumps(
            {
                "schema_version": 1,
                "packages": {
                    "fuggers_py": {"exports": []},
                    "fuggers_py.curves": {
                        "exports": [
                            {"name": "YieldCurve", "kind": "class", "owning_package": "fuggers_py.curves"},
                        ]
                    },
                    "fuggers_py.vol_surfaces": {"exports": []},
                    "fuggers_py.bonds": {"exports": []},
                    "fuggers_py.rates": {"exports": []},
                    "fuggers_py.inflation": {"exports": []},
                    "fuggers_py.credit": {"exports": []},
                    "fuggers_py.funding": {"exports": []},
                    "fuggers_py.portfolio": {"exports": []},
                },
            }
        )
        + "\n",
    )
    _git_commit_all(tmp_path, "base")
    module.freeze_public_api_structure_controls(tmp_path)
    _git_commit_all(tmp_path, "freeze controls")
    module.init_workflow(tmp_path)

    _write_text(
        tmp_path / "src" / "fuggers_py" / "curves" / "__init__.py",
        "\n".join(
            [
                "from fuggers_py.shared_curve_impl import YieldCurve",
                "",
                '__all__ = ["YieldCurve"]',
                "",
                "# changed",
                "",
            ]
        ),
    )

    result = module.validate_workflow(tmp_path, run_commands=False)

    assert result.ok is False
    assert result.reason == (
        "fuggers_py.curves export `YieldCurve` declares owner `fuggers_py.curves` but still resolves to "
        "`fuggers_py.shared_curve_impl`. Move the live implementation under `fuggers_py.curves`."
    )


def test_validate_rejects_duplicate_symbols_left_in_drain_bucket_even_if_drain_file_is_untouched(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _write_minimal_slice3_prerequisites(tmp_path)
    _write_text(
        tmp_path / "src" / "fuggers_py" / "_products" / "bonds" / "instruments.py",
        "\n".join(
            [
                "class FixedBond:",
                "    pass",
                "",
            ]
        ),
    )
    _git_commit_all(tmp_path, "base")
    module.freeze_public_api_structure_controls(tmp_path)
    _git_commit_all(tmp_path, "freeze controls")
    module.init_workflow(tmp_path)

    _write_text(
        tmp_path / "src" / "fuggers_py" / "bonds" / "instruments.py",
        "\n".join(
            [
                "class FixedBond:",
                "    pass",
                "",
            ]
        ),
    )

    result = module.validate_workflow(tmp_path, run_commands=False)

    assert result.ok is False
    assert result.reason == (
        "src/fuggers_py/_products/bonds/instruments.py still defines moved symbols that now also exist under "
        "`fuggers_py.bonds`: FixedBond. This refactor is a hard rewrite. Remove the old implementation."
    )


def test_validate_requires_frozen_current_inventory_before_later_change_sets(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _git_commit_all(tmp_path, "base")
    module.init_workflow(tmp_path)

    _write_text(tmp_path / "refactor" / "notes.md", "changed\n")

    result = module.validate_workflow(tmp_path, run_commands=False)

    assert result.ok is False
    assert result.reason == (
        "Missing `refactor/PUBLIC_API_CURRENT_INVENTORY.json`. "
        "Phase 1 slice 1 must freeze the current public and drain-list inventory before later slices."
    )


def test_validate_requires_slice2_control_files_after_inventory_freeze(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _git_commit_all(tmp_path, "base")
    module.init_workflow(tmp_path)
    _write_text(
        tmp_path / "refactor" / "PUBLIC_API_CURRENT_INVENTORY.json",
        json.dumps(
            {
                "schema_version": 1,
                "canonical_public_packages": {},
                "legacy_public_import_paths": {},
                "drain_list_inventory": {},
            }
        )
        + "\n",
    )

    _write_text(tmp_path / "refactor" / "notes.md", "changed\n")

    result = module.validate_workflow(tmp_path, run_commands=False)

    assert result.ok is False
    assert result.reason == (
        "Missing `refactor/PUBLIC_API_EXPORT_MANIFEST.json`. "
        "Phase 1 slice 2 must freeze the export manifest, legacy denylist, and migration ledger before later slices."
    )


def test_validate_requires_slice3_control_files_after_slice2_freeze(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _git_commit_all(tmp_path, "base")
    module.init_workflow(tmp_path)
    _write_text(
        tmp_path / "refactor" / "PUBLIC_API_CURRENT_INVENTORY.json",
        json.dumps(
            {
                "schema_version": 1,
                "canonical_public_packages": {},
                "legacy_public_import_paths": {},
                "drain_list_inventory": {},
            }
        )
        + "\n",
    )
    _write_text(
        tmp_path / "refactor" / "PUBLIC_API_EXPORT_MANIFEST.json",
        json.dumps({"schema_version": 1, "packages": {}}) + "\n",
    )
    _write_text(
        tmp_path / "refactor" / "PUBLIC_API_LEGACY_DENYLIST.json",
        json.dumps({"schema_version": 1, "entries": []}) + "\n",
    )
    _write_text(
        tmp_path / "refactor" / "PUBLIC_API_MIGRATION_LEDGER.json",
        json.dumps({"schema_version": 1, "entries": []}) + "\n",
    )

    _write_text(tmp_path / "refactor" / "notes.md", "changed\n")

    result = module.validate_workflow(tmp_path, run_commands=False)

    assert result.ok is False
    assert result.reason == (
        "Missing `refactor/PUBLIC_API_STRUCTURE_MANIFEST.json`. "
        "Phase 1 slice 3 must freeze the structure manifest and dependency manifest before later slices."
    )


def test_validate_rejects_structure_manifest_drift_even_when_only_source_files_change(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _write_minimal_slice3_prerequisites(tmp_path)
    _git_commit_all(tmp_path, "base")
    module.freeze_public_api_structure_controls(tmp_path)
    _git_commit_all(tmp_path, "freeze controls")
    module.init_workflow(tmp_path)

    _write_text(tmp_path / "src" / "fuggers_py" / "curves" / "internal.py", "MARKER = 1\n")

    result = module.validate_workflow(tmp_path, run_commands=False)

    assert result.ok is False
    assert result.reason == (
        "`refactor/PUBLIC_API_STRUCTURE_MANIFEST.json` no longer matches the exact `src/fuggers_py` tree. "
        "The full structure manifest must pass on every sealed change set."
    )


def test_validate_rejects_dependency_manifest_drift_even_when_only_source_files_change(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _write_minimal_slice3_prerequisites(tmp_path)
    _git_commit_all(tmp_path, "base")
    module.freeze_public_api_structure_controls(tmp_path)
    _git_commit_all(tmp_path, "freeze controls")
    module.init_workflow(tmp_path)

    _write_text(
        tmp_path / "src" / "fuggers_py" / "curves" / "__init__.py",
        "\n".join(
            [
                "from fuggers_py.vol_surfaces import Surface",
                "",
                "__all__ = []",
                "",
            ]
        ),
    )

    result = module.validate_workflow(tmp_path, run_commands=False)

    assert result.ok is False
    assert result.reason == (
        "`refactor/PUBLIC_API_DEPENDENCY_MANIFEST.json` no longer matches the exact allowed import-edge set. "
        "The full dependency manifest must pass on every sealed change set."
    )


def test_dependency_manifest_tracks_relative_from_import_aliases(tmp_path: Path) -> None:
    module = _load_validator()
    _write_minimal_slice3_prerequisites(tmp_path)
    _write_text(
        tmp_path / "src" / "fuggers_py" / "curves" / "__init__.py",
        "\n".join(
            [
                "from .. import vol_surfaces",
                "",
                "__all__ = []",
                "",
            ]
        ),
    )

    manifest = module.build_public_api_dependency_manifest(tmp_path)

    assert "fuggers_py.vol_surfaces" in manifest["packages"]["fuggers_py.curves"]["allowed_targets"]


@pytest.mark.parametrize(
    ("package_name", "import_target"),
    [
        ("curves", "fuggers_py.vol_surfaces"),
        ("vol_surfaces", "fuggers_py.curves"),
        ("bonds", "fuggers_py.curves"),
        ("rates", "fuggers_py.curves"),
        ("inflation", "fuggers_py.curves"),
        ("credit", "fuggers_py.curves"),
        ("funding", "fuggers_py.curves"),
    ],
)
def test_validate_rejects_canonical_public_import_module_router(
    tmp_path: Path,
    package_name: str,
    import_target: str,
) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _write_minimal_slice3_prerequisites(tmp_path)
    _git_commit_all(tmp_path, "base")
    module.freeze_public_api_structure_controls(tmp_path)
    _git_commit_all(tmp_path, "freeze controls")
    module.init_workflow(tmp_path)

    _write_text(
        tmp_path / "src" / "fuggers_py" / package_name / "__init__.py",
        "\n".join(
            [
                "from importlib import import_module",
                "",
                f'SurfaceModule = import_module("{import_target}")',
                "__all__ = []",
                "",
            ]
        ),
    )

    result = module.validate_workflow(tmp_path, run_commands=False)

    assert result.ok is False
    assert result.reason == (
        f"src/fuggers_py/{package_name}/__init__.py uses `import_module` in a canonical public package. "
        "Canonical public packages must use direct imports only."
    )


@pytest.mark.parametrize(
    "package_name",
    ["curves", "vol_surfaces", "bonds", "rates", "inflation", "credit", "funding"],
)
def test_validate_rejects_canonical_public___getattr__(tmp_path: Path, package_name: str) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _write_minimal_slice3_prerequisites(tmp_path)
    _git_commit_all(tmp_path, "base")
    module.freeze_public_api_structure_controls(tmp_path)
    _git_commit_all(tmp_path, "freeze controls")
    module.init_workflow(tmp_path)

    _write_text(
        tmp_path / "src" / "fuggers_py" / package_name / "__init__.py",
        "\n".join(
            [
                "def __getattr__(name: str):",
                "    raise AttributeError(name)",
                "",
            ]
        ),
    )

    result = module.validate_workflow(tmp_path, run_commands=False)

    assert result.ok is False
    assert result.reason == (
        f"src/fuggers_py/{package_name}/__init__.py uses `__getattr__` in a canonical public package. "
        "Canonical public packages must use direct imports only."
    )


def test_validate_rejects_canonical_public___module___reassignment(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _write_minimal_slice3_prerequisites(tmp_path)
    _git_commit_all(tmp_path, "base")
    module.freeze_public_api_structure_controls(tmp_path)
    _git_commit_all(tmp_path, "freeze controls")
    module.init_workflow(tmp_path)

    _write_text(
        tmp_path / "src" / "fuggers_py" / "curves" / "__init__.py",
        "\n".join(
            [
                "class Curve:",
                "    pass",
                "",
                "Curve.__module__ = __name__",
                "",
            ]
        ),
    )

    result = module.validate_workflow(tmp_path, run_commands=False)

    assert result.ok is False
    assert result.reason == (
        "src/fuggers_py/curves/__init__.py reassigns `__module__` in a canonical public package. "
        "Move the code to the real owner instead of rewriting ownership metadata."
    )


def test_validate_rejects_unchanged_canonical_public_router_outside_change_set(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _write_minimal_slice3_prerequisites(tmp_path)
    _write_text(
        tmp_path / "src" / "fuggers_py" / "curves" / "__init__.py",
        "\n".join(
            [
                "from importlib import import_module",
                "",
                "SurfaceModule = import_module(\"fuggers_py.vol_surfaces\")",
                "__all__ = []",
                "",
            ]
        ),
    )
    _write_text(
        tmp_path / "src" / "fuggers_py" / "bonds" / "__init__.py",
        "\n".join(
            [
                "from importlib import import_module",
                "",
                "def __getattr__(name: str):",
                "    return getattr(import_module(\"fuggers_py.curves\"), name)",
                "",
            ]
        ),
    )
    _git_commit_all(tmp_path, "base")
    module.freeze_public_api_structure_controls(tmp_path)
    _git_commit_all(tmp_path, "freeze controls")
    module.init_workflow(tmp_path)

    _write_text(tmp_path / "refactor" / "notes.md", "changed\n")

    result = module.validate_workflow(tmp_path, run_commands=False)

    assert result.ok is False
    assert result.reason == (
        "src/fuggers_py/bonds/__init__.py uses `__getattr__` in a canonical public package. "
        "Canonical public packages must use direct imports only."
    )


def test_validate_rejects_unchanged_canonical_public___module___reassignment_outside_change_set(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _write_minimal_slice3_prerequisites(tmp_path)
    _write_text(
        tmp_path / "src" / "fuggers_py" / "bonds" / "products.py",
        "\n".join(
            [
                "class Bond:",
                "    pass",
                "",
                "Bond.__module__ = __name__",
                "",
            ]
        ),
    )
    _git_commit_all(tmp_path, "base")
    module.freeze_public_api_structure_controls(tmp_path)
    _git_commit_all(tmp_path, "freeze controls")
    module.init_workflow(tmp_path)

    _write_text(tmp_path / "refactor" / "notes.md", "changed\n")

    result = module.validate_workflow(tmp_path, run_commands=False)

    assert result.ok is False
    assert result.reason == (
        "src/fuggers_py/bonds/products.py reassigns `__module__` in a canonical public package. "
        "Move the code to the real owner instead of rewriting ownership metadata."
    )


def test_dynamic_router_inventory_tracks_unchanged_public_entrypoints(tmp_path: Path) -> None:
    module = _load_validator()
    _write_minimal_slice3_prerequisites(tmp_path)
    _write_text(
        tmp_path / "src" / "fuggers_py" / "curves" / "__init__.py",
        "\n".join(
            [
                "from importlib import import_module",
                "",
                "def __getattr__(name: str):",
                "    return getattr(import_module(\"fuggers_py.vol_surfaces\"), name)",
                "",
            ]
        ),
    )
    _write_text(
        tmp_path / "src" / "fuggers_py" / "bonds" / "__init__.py",
        "\n".join(
            [
                "from importlib import import_module",
                "",
                "def __getattr__(name: str):",
                "    return getattr(import_module(\"fuggers_py.curves\"), name)",
                "",
            ]
        ),
    )

    inventory = module._canonical_public_dynamic_import_inventory(tmp_path)

    assert inventory == {
        "src/fuggers_py/bonds/__init__.py": ["__getattr__", "import_module"],
        "src/fuggers_py/curves/__init__.py": ["__getattr__", "import_module"],
    }


def test_validate_rejects_frozen_planning_artifact_changes_mixed_with_implementation_files(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _write_minimal_slice3_prerequisites(tmp_path)
    _git_commit_all(tmp_path, "base")
    module.freeze_public_api_structure_controls(tmp_path)
    _git_commit_all(tmp_path, "freeze controls")
    module.init_workflow(tmp_path)

    structure_manifest_path = tmp_path / "refactor" / "PUBLIC_API_STRUCTURE_MANIFEST.json"
    structure_manifest = json.loads(structure_manifest_path.read_text(encoding="utf-8"))
    structure_manifest["top_level_packages"]["_market"] = {
        "role": "transition_bucket",
        "planned_action": "delete",
    }
    _write_text(structure_manifest_path, json.dumps(structure_manifest, indent=2, sort_keys=True) + "\n")
    _write_text(tmp_path / "src" / "fuggers_py" / "bonds" / "products.py", "MARKER = 1\n")

    result = module.validate_workflow(tmp_path, run_commands=False)

    assert result.ok is False
    assert result.reason == (
        "Frozen planning artifacts changed together with non-planning files. "
        "Planning artifacts: refactor/PUBLIC_API_STRUCTURE_MANIFEST.json. "
        "Non-planning files: src/fuggers_py/bonds/products.py. "
        "Update target docs or control manifests only in a separate planning change set."
    )


def test_status_reports_unchanged_canonical_public_router_audit(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _write_minimal_slice3_prerequisites(tmp_path)
    _write_text(
        tmp_path / "src" / "fuggers_py" / "curves" / "__init__.py",
        "\n".join(
            [
                "from importlib import import_module",
                "",
                "def __getattr__(name: str):",
                "    return getattr(import_module(\"fuggers_py.vol_surfaces\"), name)",
                "",
            ]
        ),
    )
    _write_text(
        tmp_path / "src" / "fuggers_py" / "credit" / "__init__.py",
        "\n".join(
            [
                "from importlib import import_module",
                "",
                "def __getattr__(name: str):",
                "    return getattr(import_module(\"fuggers_py.curves\"), name)",
                "",
            ]
        ),
    )
    _git_commit_all(tmp_path, "base")
    module.freeze_public_api_structure_controls(tmp_path)
    _git_commit_all(tmp_path, "freeze controls")
    module.init_workflow(tmp_path)
    _write_text(tmp_path / "refactor" / "notes.md", "changed\n")

    message = module._status_message(tmp_path)

    assert (
        "Canonical public router audit: 2 entrypoint file(s) outside the current change set still use dynamic routing primitives."
        in message
    )


def test_freeze_inventory_writes_canonical_packages_and_drain_list_snapshot(tmp_path: Path) -> None:
    module = _load_validator()

    public_modules = (
        "curves",
        "vol_surfaces",
        "bonds",
        "rates",
        "inflation",
        "credit",
        "funding",
        "portfolio",
    )

    _write_text(
        tmp_path / "src" / "fuggers_py" / "__init__.py",
        "\n".join(
            [
                "from . import curves",
                "",
                "Shared = \"shared\"",
                "__all__ = [\"curves\", \"Shared\"]",
                "",
            ]
        ),
    )
    _write_text(
        tmp_path / "src" / "fuggers_py" / "curves" / "__init__.py",
        "\n".join(
            [
                "Marker = \"curve\"",
                "__all__ = [\"Marker\"]",
                "",
            ]
        ),
    )
    for module_name in public_modules[1:]:
        _write_text(tmp_path / "src" / "fuggers_py" / module_name / "__init__.py", "__all__ = []\n")

    _write_text(
        tmp_path / "src" / "fuggers_py" / "_market" / "__init__.py",
        "\n".join(
            [
                "from .helpers import QuoteSide",
                "__all__ = [\"QuoteSide\"]",
                "",
            ]
        ),
    )
    _write_text(
        tmp_path / "src" / "fuggers_py" / "_market" / "helpers.py",
        "\n".join(
            [
                "class QuoteSide:",
                "    pass",
                "",
            ]
        ),
    )
    _write_text(
        tmp_path / "tests" / "contracts" / "api" / "test_legacy_public_modules_absent.py",
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import pytest",
                "",
                "",
                "@pytest.mark.parametrize(",
                '    "module_name",',
                '    ["fuggers_py.market"],',
                ")",
                "def test_non_target_public_modules_are_not_importable(module_name: str) -> None:",
                "    assert module_name == \"fuggers_py.market\"",
                "",
            ]
        ),
    )

    output_path = tmp_path / "refactor" / "PUBLIC_API_CURRENT_INVENTORY.json"
    module.freeze_public_api_current_inventory(tmp_path, output_path=output_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == 1
    assert payload["canonical_public_packages"]["fuggers_py"]["all"] == ["curves", "Shared"]
    assert payload["canonical_public_packages"]["fuggers_py"]["exports"] == [
        {
            "name": "curves",
            "kind": "module",
            "resolved_module": "fuggers_py.curves",
            "resolved_file": "src/fuggers_py/curves/__init__.py",
        },
        {
            "name": "Shared",
            "kind": "constant",
            "resolved_module": None,
            "resolved_file": None,
        },
    ]
    assert payload["legacy_public_import_paths"]["retired_contract_paths"] == ["fuggers_py.market"]
    assert payload["legacy_public_import_paths"]["currently_importable"] == []

    market_modules = payload["drain_list_inventory"]["_market"]["modules"]
    assert [module_row["module"] for module_row in market_modules] == [
        "fuggers_py._market",
        "fuggers_py._market.helpers",
    ]
    assert market_modules[0]["exported_names"] == ["QuoteSide"]
    assert market_modules[0]["public_symbols"] == [
        {
            "name": "QuoteSide",
            "kind": "import",
            "in___all__": True,
            "is_alias": True,
        }
    ]
    assert market_modules[1]["public_symbols"] == [
        {
            "name": "QuoteSide",
            "kind": "class",
            "in___all__": False,
            "is_alias": False,
        }
    ]


def test_freeze_inventory_rejects_root_module_export_missing_plain_attribute_binding(tmp_path: Path) -> None:
    module = _load_validator()

    _write_text(
        tmp_path / "src" / "fuggers_py" / "__init__.py",
        "\n".join(
            [
                '__all__ = ["credit"]',
                "",
            ]
        ),
    )
    _write_text(tmp_path / "src" / "fuggers_py" / "credit" / "__init__.py", "__all__ = []\n")
    _write_text(
        tmp_path / "tests" / "contracts" / "api" / "test_legacy_public_modules_absent.py",
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "def test_non_target_public_modules_are_not_importable() -> None:",
                "    assert True",
                "",
            ]
        ),
    )

    with pytest.raises(
        ValueError,
        match=r"fuggers_py exports `credit` in __all__ but does not bind it on plain attribute access\.",
    ):
        module.freeze_public_api_current_inventory(tmp_path, output_path=tmp_path / "refactor" / "PUBLIC_API_CURRENT_INVENTORY.json")


def test_moved_phase1_symbol_import_errors_reject_old_bucket_routes(tmp_path: Path) -> None:
    module = _load_validator()
    _write_text(
        tmp_path / "src" / "fuggers_py" / "_reference" / "bonds" / "conventions" / "us_treasury.py",
        "from ..types import YieldCalculationRules\n",
    )
    _write_text(
        tmp_path / "tests" / "unit" / "test_rates_shared_types.py",
        "from fuggers_py._products.rates import PayReceive\n",
    )

    errors = module._moved_phase1_symbol_import_errors(
        tmp_path,
        {
            "src/fuggers_py/_reference/bonds/conventions/us_treasury.py",
            "tests/unit/test_rates_shared_types.py",
        },
    )

    assert errors == [
        "src/fuggers_py/_reference/bonds/conventions/us_treasury.py:1 imports moved Phase 1 name `YieldCalculationRules` from old bucket module `fuggers_py._reference.bonds.types`. Import it from `fuggers_py._core` instead.",
        "tests/unit/test_rates_shared_types.py:1 imports moved Phase 1 name `PayReceive` from old bucket module `fuggers_py._products.rates`. Import it from `fuggers_py._core` instead.",
    ]


def test_core_self_contained_import_errors_reject_old_reference_bond_support(tmp_path: Path) -> None:
    module = _load_validator()
    _write_text(
        tmp_path / "src" / "fuggers_py" / "_core" / "yield_calculation_rules.py",
        "from fuggers_py._reference.bonds.types.yield_convention import YieldConvention\n",
    )

    errors = module._core_self_contained_import_errors(
        tmp_path,
        {"src/fuggers_py/_core/yield_calculation_rules.py"},
    )

    assert errors == [
        "src/fuggers_py/_core/yield_calculation_rules.py imports old bond support module "
        "`fuggers_py._reference.bonds.types.yield_convention`. "
        "`fuggers_py._core` owners must import shared support from local `_core` modules instead."
    ]


def test_freeze_export_controls_writes_manifest_denylist_and_ledger(tmp_path: Path) -> None:
    module = _load_validator()

    canonical_public_packages = {
        "fuggers_py": {
            "exports": [
                {
                    "name": "PayReceive",
                    "kind": "class",
                    "resolved_module": "fuggers_py._core.pay_receive",
                    "resolved_file": "src/fuggers_py/_core/pay_receive.py",
                },
                {
                    "name": "Tenor",
                    "kind": "class",
                    "resolved_module": "fuggers_py._core.tenor",
                    "resolved_file": "src/fuggers_py/_core/tenor.py",
                },
                {
                    "name": "curves",
                    "kind": "module",
                    "resolved_module": "fuggers_py.curves",
                    "resolved_file": "src/fuggers_py/curves/__init__.py",
                },
            ]
        },
        "fuggers_py.curves": {
            "exports": [
                {
                    "name": "YieldCurve",
                    "kind": "class",
                    "resolved_module": "fuggers_py._curves_impl.rates.base",
                    "resolved_file": "src/fuggers_py/_curves_impl/rates/base.py",
                }
            ]
        },
        "fuggers_py.vol_surfaces": {"exports": []},
        "fuggers_py.bonds": {"exports": []},
        "fuggers_py.rates": {"exports": []},
        "fuggers_py.inflation": {"exports": []},
        "fuggers_py.credit": {"exports": []},
        "fuggers_py.funding": {"exports": []},
        "fuggers_py.portfolio": {"exports": []},
    }
    drain_list_inventory = {
        "_market": {
            "modules": [
                {
                    "module": "fuggers_py._market",
                    "file": "src/fuggers_py/_market/__init__.py",
                    "public_symbols": [
                        {
                            "name": "QuoteSide",
                            "kind": "import",
                            "in___all__": True,
                            "is_alias": True,
                        }
                    ],
                }
            ]
        },
        "_products": {"modules": []},
        "_pricers": {"modules": []},
        "_measures": {"modules": []},
        "_reference": {"modules": []},
        "_calc": {"modules": []},
        "_adapters": {"modules": []},
        "_curves_impl": {"modules": []},
        "_vol_surfaces_impl": {"modules": []},
    }
    _write_text(
        tmp_path / "refactor" / "PUBLIC_API_CURRENT_INVENTORY.json",
        json.dumps(
            {
                "schema_version": 1,
                "canonical_public_packages": canonical_public_packages,
                "legacy_public_import_paths": {
                    "currently_importable": [],
                    "retired_contract_paths": [
                        "fuggers_py.market.curves",
                        "fuggers_py.market.snapshot",
                    ],
                },
                "drain_list_inventory": drain_list_inventory,
            }
        )
        + "\n",
    )

    written = module.freeze_public_api_export_controls(tmp_path)

    assert [path.name for path in written] == [
        "PUBLIC_API_EXPORT_MANIFEST.json",
        "PUBLIC_API_LEGACY_DENYLIST.json",
        "PUBLIC_API_MIGRATION_LEDGER.json",
    ]

    manifest = json.loads((tmp_path / "refactor" / "PUBLIC_API_EXPORT_MANIFEST.json").read_text(encoding="utf-8"))
    denylist = json.loads((tmp_path / "refactor" / "PUBLIC_API_LEGACY_DENYLIST.json").read_text(encoding="utf-8"))
    ledger = json.loads((tmp_path / "refactor" / "PUBLIC_API_MIGRATION_LEDGER.json").read_text(encoding="utf-8"))

    root_exports = {row["name"]: row for row in manifest["packages"]["fuggers_py"]["exports"]}
    assert root_exports["curves"]["owning_package"] == "fuggers_py.curves"
    assert root_exports["Tenor"]["owning_package"] == "fuggers_py._core"
    assert root_exports["PayReceive"]["owning_package"] == "fuggers_py._core"

    denylist_entries = {row["legacy_import_path"]: row for row in denylist["entries"]}
    assert denylist_entries["fuggers_py.market.curves"]["replacement_import_path"] == "fuggers_py.curves"
    assert denylist_entries["fuggers_py.market.snapshot"]["replacement_import_path"] is None

    ledger_entries = {row["entry_id"]: row for row in ledger["entries"]}
    assert ledger_entries["public:fuggers_py:Tenor"]["decision"] == "move to fuggers_py._core"
    assert ledger_entries["drain:fuggers_py._market:QuoteSide"]["decision"] == "delete"


def test_freeze_structure_controls_writes_structure_and_dependency_manifests(tmp_path: Path) -> None:
    module = _load_validator()
    _write_text(tmp_path / "src" / "fuggers_py" / "__init__.py", "__all__ = []\n")

    for package_name in [
        "_core",
        "_math",
        "_runtime",
        "_storage",
        "_products",
        "curves",
        "vol_surfaces",
        "bonds",
        "rates",
        "inflation",
        "credit",
        "funding",
        "portfolio",
    ]:
        package_dir = tmp_path / "src" / "fuggers_py" / package_name
        package_dir.mkdir(parents=True, exist_ok=True)
        _write_text(package_dir / "__init__.py", "__all__ = []\n")

    _write_text(tmp_path / "src" / "fuggers_py" / "bonds" / "products.py", "from fuggers_py._core import Date\n")
    _write_text(tmp_path / "src" / "fuggers_py" / "portfolio" / "results.py", "from fuggers_py._storage import storage\n")
    _write_text(tmp_path / "src" / "fuggers_py" / "portfolio" / "analytics" / "__init__.py", "__all__ = []\n")

    _write_text(
        tmp_path / "refactor" / "PUBLIC_API_EXPORT_MANIFEST.json",
        json.dumps(
            {
                "schema_version": 1,
                "packages": {
                    "fuggers_py": {
                        "exports": [
                            {"name": "curves", "kind": "module", "owning_package": "fuggers_py.curves"},
                            {"name": "Date", "kind": "class", "owning_package": "fuggers_py._core"},
                        ]
                    },
                    "fuggers_py.curves": {"exports": []},
                    "fuggers_py.vol_surfaces": {"exports": []},
                    "fuggers_py.bonds": {"exports": []},
                    "fuggers_py.rates": {"exports": []},
                    "fuggers_py.inflation": {"exports": []},
                    "fuggers_py.credit": {"exports": []},
                    "fuggers_py.funding": {"exports": []},
                    "fuggers_py.portfolio": {"exports": []},
                },
            }
        )
        + "\n",
    )

    written = module.freeze_public_api_structure_controls(tmp_path)

    assert [path.name for path in written] == [
        "PUBLIC_API_STRUCTURE_MANIFEST.json",
        "PUBLIC_API_DEPENDENCY_MANIFEST.json",
    ]

    structure = json.loads((tmp_path / "refactor" / "PUBLIC_API_STRUCTURE_MANIFEST.json").read_text(encoding="utf-8"))
    dependency = json.loads((tmp_path / "refactor" / "PUBLIC_API_DEPENDENCY_MANIFEST.json").read_text(encoding="utf-8"))

    assert structure["top_level_packages"]["_products"] == {
        "role": "transition_bucket",
        "planned_action": "delete",
    }
    assert structure["top_level_packages"]["_core"] == {
        "role": "internal_survivor",
        "planned_action": "keep",
    }
    assert structure["top_level_packages"]["bonds"] == {
        "role": "canonical_public",
        "planned_action": "keep",
    }
    assert "products.py" in structure["canonical_public_package_trees"]["bonds"]
    assert "analytics/" in structure["canonical_public_package_trees"]["portfolio"]
    assert "results.py" in structure["canonical_public_package_trees"]["portfolio"]

    assert dependency["packages"]["fuggers_py"]["allowed_targets"] == [
        "fuggers_py._core",
        "fuggers_py.bonds",
        "fuggers_py.credit",
        "fuggers_py.curves",
        "fuggers_py.funding",
        "fuggers_py.inflation",
        "fuggers_py.portfolio",
        "fuggers_py.rates",
        "fuggers_py.vol_surfaces",
    ]
    assert "fuggers_py._storage" in dependency["packages"]["fuggers_py.portfolio"]["allowed_targets"]


def test_validate_rejects_thin_legacy_wrapper_in_hard_rewrite(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _git_commit_all(tmp_path, "base")
    _freeze_minimal_slice3_baseline(tmp_path, module)

    _write_text(tmp_path / "src" / "fuggers_py" / "curves" / "__init__.py", "__all__ = []\n")
    _write_text(
        tmp_path / "src" / "fuggers_py" / "market" / "bridge.py",
        "\n".join(
            [
                "from fuggers_py.curves import YieldCurve",
                "",
                "__all__ = [\"YieldCurve\"]",
                "",
            ]
        ),
    )

    result = module.validate_workflow(tmp_path, run_commands=False)

    assert result.ok is False
    assert result.reason == (
        "src/fuggers_py/market/bridge.py is a compatibility wrapper in a legacy namespace. "
        "This refactor is a hard rewrite. Delete the old public path instead of re-exporting the new module."
    )


def test_complete_requires_matching_reviewer_artifact_and_advances_baseline(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _write_minimal_slice3_prerequisites(tmp_path)
    _git_commit_all(tmp_path, "base")
    module.init_workflow(tmp_path)
    module.freeze_public_api_structure_controls(tmp_path)
    _write_text(tmp_path / "refactor" / "notes.md", "changed\n")

    validate_result = module.validate_workflow(tmp_path, run_commands=False)

    assert validate_result.ok is True
    assert validate_result.fingerprint is not None

    _write_text(
        module._default_review_path(tmp_path),
        "\n".join(
            [
                "# public_api_reviewer",
                "Workflow: public-api-refactor",
                f"Fingerprint: {validate_result.fingerprint}",
                "Status: complete",
                "",
                "## Findings",
                "- None.",
                "",
                "## Boundary risks",
                "- None.",
                "",
                "## Missing deterministic checks",
                "- None.",
                "",
                "## Verdict",
                "- approve",
                "",
            ]
        ),
    )

    complete_result = module.complete_workflow(
        tmp_path,
        review_path=module._default_review_path(tmp_path),
        run_commands=False,
    )
    state = module._load_state(tmp_path)

    assert complete_result.ok is True
    assert state is not None
    assert state["baseline_changed_paths"] == [
        "refactor/PUBLIC_API_DEPENDENCY_MANIFEST.json",
        "refactor/PUBLIC_API_STRUCTURE_MANIFEST.json",
        "refactor/notes.md",
    ]


def test_stop_hook_blocks_without_fresh_reviewer_approval(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _write_minimal_slice3_prerequisites(tmp_path)
    _git_commit_all(tmp_path, "base")
    module.init_workflow(tmp_path)
    module.freeze_public_api_structure_controls(tmp_path)
    _write_text(tmp_path / "refactor" / "notes.md", "changed\n")

    validate_result = module.validate_workflow(tmp_path, run_commands=False)
    assert validate_result.ok is True
    module._mark_validation_state(
        tmp_path,
        ok=True,
        reason="Checkpoint public API refactor validation passed.",
        fingerprint=validate_result.fingerprint,
    )

    original_stdin = sys.stdin
    buffer = io.StringIO()
    try:
        sys.stdin = io.StringIO('{"stop_hook_active": true}')
        with redirect_stdout(buffer):
            exit_code = module._handle_stop_hook(tmp_path)
    finally:
        sys.stdin = original_stdin

    payload = json.loads(buffer.getvalue())

    assert exit_code == 0
    assert payload["continue"] is False
    assert "Spawn `public_api_reviewer`" in payload["stopReason"]


def test_status_reports_inactive_when_workflow_has_not_started(tmp_path: Path) -> None:
    module = _load_validator()

    message = module._status_message(tmp_path)

    assert message == (
        "Public API refactor workflow is not active. "
        "Start it with `python tools/validate_public_api_refactor.py init`."
    )


def test_user_prompt_hook_does_not_create_state_for_plain_prompt_when_inactive(tmp_path: Path) -> None:
    module = _load_validator()

    original_stdin = sys.stdin
    buffer = io.StringIO()
    try:
        sys.stdin = io.StringIO('{"prompt": "Update one unit test."}')
        with redirect_stdout(buffer):
            exit_code = module._handle_user_prompt_hook(tmp_path)
    finally:
        sys.stdin = original_stdin

    assert exit_code == 0
    assert buffer.getvalue() == ""
    assert module._load_state(tmp_path) is None


def test_user_prompt_hook_auto_activates_on_trigger_prompt(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _git_commit_all(tmp_path, "base")

    original_stdin = sys.stdin
    buffer = io.StringIO()
    try:
        sys.stdin = io.StringIO('{"prompt": "Start the public API refactor and move to the new public structure."}')
        with redirect_stdout(buffer):
            exit_code = module._handle_user_prompt_hook(tmp_path)
    finally:
        sys.stdin = original_stdin

    payload = json.loads(buffer.getvalue())
    state = module._load_state(tmp_path)

    assert exit_code == 0
    assert state is not None
    assert state["active"] is True
    assert "PUBLIC_API_TARGET_STATE.md" in payload["hookSpecificOutput"]["additionalContext"]


def test_user_prompt_hook_injects_for_every_prompt_while_active(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _git_commit_all(tmp_path, "base")
    module.init_workflow(tmp_path)

    original_stdin = sys.stdin
    buffer = io.StringIO()
    try:
        sys.stdin = io.StringIO('{"prompt": "Move one helper."}')
        with redirect_stdout(buffer):
            exit_code = module._handle_user_prompt_hook(tmp_path)
    finally:
        sys.stdin = original_stdin

    payload = json.loads(buffer.getvalue())

    assert exit_code == 0
    assert "public_api_reviewer" in payload["hookSpecificOutput"]["additionalContext"]
    assert "hard rewrite" in payload["hookSpecificOutput"]["additionalContext"]


def test_deactivate_turns_off_active_workflow(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    _write_text(tmp_path / "README.md", "base\n")
    _git_commit_all(tmp_path, "base")
    module.init_workflow(tmp_path)

    message = module.deactivate_workflow(tmp_path)
    state = module._load_state(tmp_path)

    assert message == "Deactivated public API refactor workflow."
    assert state is not None
    assert state["active"] is False


def test_public_api_reviewer_agent_is_pinned_to_gpt54_xhigh_read_only() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    payload = tomllib.loads((repo_root / ".codex" / "agents" / "public_api_reviewer.toml").read_text(encoding="utf-8"))

    assert payload["name"] == "public_api_reviewer"
    assert payload["model"] == "gpt-5.4"
    assert payload["model_reasoning_effort"] == "xhigh"
    assert payload["sandbox_mode"] == "read-only"


def test_hooks_wire_public_api_refactor_validator() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    payload = json.loads((repo_root / ".codex" / "hooks.json").read_text(encoding="utf-8"))

    user_prompt_commands = [
        hook["command"]
        for group in payload["hooks"]["UserPromptSubmit"]
        for hook in group["hooks"]
    ]
    stop_commands = [
        hook["command"]
        for group in payload["hooks"]["Stop"]
        for hook in group["hooks"]
    ]

    assert any("tools/validate_public_api_refactor.py\" user-prompt-hook" in command for command in user_prompt_commands)
    assert any("tools/validate_public_api_refactor.py\" stop-hook" in command for command in stop_commands)
