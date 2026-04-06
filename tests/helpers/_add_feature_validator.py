from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_validator_module() -> ModuleType:
    module_path = REPO_ROOT / "tools" / "validate_add_feature.py"
    spec = importlib.util.spec_from_file_location("validate_add_feature_module", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def complete_spec(
    module: ModuleType,
    root: Path,
    feature_slug: str,
    *,
    required_categories: list[str] | None = None,
) -> None:
    spec_path = module._spec_path(root, feature_slug)
    payload = module._json_load(spec_path)
    payload["summary"] = {
        "problem": "Validator checkpoints are too heavy.",
        "outcome": "Checkpoint validation stays fast and final validation stays strict.",
    }
    payload["public_api"] = {
        "new_symbols": [],
        "changed_symbols": [],
        "backward_compatibility": "Final mark-passed validation remains the strict completion gate.",
        "docs_examples_to_update": [],
    }
    payload["formulas_or_rules"] = [
        "Checkpoint validation runs only the fast command set.",
        "Completion validation includes the heavyweight repo-wide command set.",
    ]
    payload["conventions"] = ["Use feature-owned tests to cover the command split."]
    payload["accepted_inputs"] = [
        "validate",
        "validate --full",
        "validate --mark-passed",
    ]
    payload["rejected_inputs"] = ["Do not run source coverage during ordinary checkpoint validation."]
    payload["edge_cases"] = ["Full validation without mark-passed leaves workflow state active."]
    payload["invariants"] = [
        "Feature-owned tests stay required.",
        "Final validation still runs the heavyweight repo gate.",
    ]
    payload["numerical_tolerance"] = {
        "absolute": "0",
        "relative": "0",
        "notes": "Tooling-only behavior change.",
    }
    payload["required_test_categories"] = required_categories or ["unit", "validation", "properties"]
    module._json_dump(spec_path, payload)


def complete_reviews(module: ModuleType, root: Path, feature_slug: str) -> None:
    for reviewer_name in module.REVIEWER_NAMES:
        module._review_path(root, feature_slug, reviewer_name).write_text(
            "\n".join(
                [
                    f"# {reviewer_name}",
                    f"Feature: {feature_slug}",
                    "Status: complete",
                    "",
                    "## Findings",
                    "- None.",
                    "",
                    "## Missing tests",
                    "- None.",
                    "",
                    "## Open questions",
                    "- None.",
                    "",
                    "## Verdict",
                    "- approve",
                    "",
                ]
            ),
            encoding="utf-8",
        )


def write_feature_test(root: Path, relative_path: str, feature_slug: str, category: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "import pytest",
                "",
                f"@pytest.mark.feature_slug(\"{feature_slug}\")",
                f"@pytest.mark.feature_category(\"{category}\")",
                "def test_example() -> None:",
                "    assert True",
                "",
            ]
        ),
        encoding="utf-8",
    )


def init_complete_workflow(root: Path, feature_slug: str) -> ModuleType:
    module = load_validator_module()
    module.init_workflow(root, feature_slug)
    complete_spec(module, root, feature_slug)
    complete_reviews(module, root, feature_slug)
    write_feature_test(root, "tests/unit/test_feature_unit.py", feature_slug, "unit")
    write_feature_test(
        root,
        "tests/integration/validation/test_feature_validation.py",
        feature_slug,
        "validation",
    )
    write_feature_test(
        root,
        "tests/integration/properties/test_feature_properties.py",
        feature_slug,
        "properties",
    )
    return module
