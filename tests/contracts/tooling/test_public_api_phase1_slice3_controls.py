from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_validator():
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "tools" / "validate_public_api_refactor.py"
    spec = importlib.util.spec_from_file_location("validate_public_api_refactor_module_slice3", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_phase1_slice3_control_files_match_the_generator() -> None:
    module = _load_validator()
    repo_root = Path(__file__).resolve().parents[3]

    expected_structure = json.loads((repo_root / "refactor" / "PUBLIC_API_STRUCTURE_MANIFEST.json").read_text(encoding="utf-8"))
    expected_dependency = json.loads((repo_root / "refactor" / "PUBLIC_API_DEPENDENCY_MANIFEST.json").read_text(encoding="utf-8"))

    assert module.build_public_api_structure_manifest(repo_root) == expected_structure
    assert module.build_public_api_dependency_manifest(repo_root) == expected_dependency


def test_phase1_slice3_control_files_capture_live_structure_and_allowed_edges() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    structure = json.loads((repo_root / "refactor" / "PUBLIC_API_STRUCTURE_MANIFEST.json").read_text(encoding="utf-8"))
    dependency = json.loads((repo_root / "refactor" / "PUBLIC_API_DEPENDENCY_MANIFEST.json").read_text(encoding="utf-8"))

    assert structure["schema_version"] == 1
    assert structure["phase"] == "phase1_slice3"
    assert structure["root_package"] == "fuggers_py"
    assert structure["top_level_packages"]["_products"] == {
        "role": "transition_bucket",
        "planned_action": "delete",
    }
    assert structure["top_level_packages"]["_core"] == {
        "role": "internal_survivor",
        "planned_action": "keep",
    }
    assert structure["top_level_packages"]["curves"] == {
        "role": "canonical_public",
        "planned_action": "keep",
    }
    assert "_curves_impl" not in structure["top_level_packages"]
    assert structure["canonical_public_package_trees"]["curves"] == [
        "__init__.py",
        "base.py",
        "calibrators/",
        "calibrators/__init__.py",
        "calibrators/_quotes.py",
        "calibrators/base.py",
        "calibrators/bootstrap.py",
        "calibrators/global_fit.py",
        "conversion.py",
        "date_support.py",
        "enums.py",
        "errors.py",
        "kernels/",
        "kernels/__init__.py",
        "kernels/base.py",
        "kernels/composite.py",
        "kernels/decorators.py",
        "kernels/nodes.py",
        "kernels/parametric.py",
        "kernels/spline.py",
        "multicurve/",
        "multicurve/__init__.py",
        "multicurve/index.py",
        "reports.py",
        "spec.py",
    ]
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
    assert dependency["packages"]["fuggers_py.curves"]["allowed_targets"] == [
        "fuggers_py._core",
        "fuggers_py._math",
        "fuggers_py.bonds",
        "fuggers_py.credit",
        "fuggers_py.funding",
        "fuggers_py.inflation",
        "fuggers_py.rates",
    ]
    assert "fuggers_py._runtime" in dependency["packages"]["fuggers_py.portfolio"]["allowed_targets"]
    assert "fuggers_py._storage" in dependency["packages"]["fuggers_py.portfolio"]["allowed_targets"]
