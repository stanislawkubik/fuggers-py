from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType


def _load_validator() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "tools" / "validate_add_feature.py"
    spec = importlib.util.spec_from_file_location("validate_add_feature_module", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _complete_spec(module: ModuleType, root: Path, feature_slug: str, *, include_public_api_change: bool = False) -> None:
    spec_path = module._spec_path(root, feature_slug)
    payload = module._json_load(spec_path)
    payload["summary"] = {"problem": "Add the feature.", "outcome": "Expose the feature."}
    payload["public_api"] = {
        "new_symbols": ["fuggers_py.measures.example"] if include_public_api_change else [],
        "changed_symbols": [],
        "backward_compatibility": "Additive only.",
        "docs_examples_to_update": [],
    }
    payload["formulas_or_rules"] = ["Round-trip identity must hold."]
    payload["conventions"] = ["Spread outputs use decimal form."]
    payload["accepted_inputs"] = ["Fixed-rate bonds."]
    payload["rejected_inputs"] = ["Unsupported callable structures."]
    payload["edge_cases"] = ["Negative rates."]
    payload["invariants"] = ["Price solve round-trips."]
    payload["numerical_tolerance"] = {"absolute": "1e-10", "relative": "1e-8", "notes": "Tight default."}
    module._json_dump(spec_path, payload)


def _complete_reviews(module: ModuleType, root: Path, feature_slug: str) -> None:
    for reviewer_name in module.REVIEWER_NAMES:
        extra_section = ["## Independent test ideas", "- None."] if reviewer_name != "fi_diff_reviewer" else [
            "## Hidden blind spots",
            "- None.",
        ]
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
                    *extra_section,
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


def _write_feature_test(root: Path, relative_path: str, feature_slug: str, category: str) -> None:
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


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "tests@example.com"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Tests"], cwd=root, check=True, capture_output=True, text=True)


def _git_commit_all(root: Path, message: str) -> None:
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", message], cwd=root, check=True, capture_output=True, text=True)


def test_init_creates_state_spec_and_review_placeholders(tmp_path: Path) -> None:
    module = _load_validator()

    module.init_workflow(tmp_path, "sample-feature", request_text="Add sample feature.")

    spec_path = module._spec_path(tmp_path, "sample-feature")
    state_path = module._state_path(tmp_path)

    assert spec_path.exists()
    assert state_path.exists()
    assert spec_path == tmp_path / ".tmp" / "add-feature" / "specs" / "sample-feature.json"
    assert state_path == tmp_path / ".tmp" / "add-feature" / ".state.json"
    for reviewer_name in module.REVIEWER_NAMES:
        review_path = module._review_path(tmp_path, "sample-feature", reviewer_name)
        assert review_path.exists()
        assert review_path.parent == tmp_path / ".tmp" / "add-feature" / "reviews"

    payload = json.loads(spec_path.read_text(encoding="utf-8"))
    assert payload["feature_slug"] == "sample-feature"
    assert payload["required_test_categories"] == ["unit", "validation", "properties"]


def test_validate_requires_all_required_categories(tmp_path: Path) -> None:
    module = _load_validator()

    module.init_workflow(tmp_path, "sample-feature")
    _complete_spec(module, tmp_path, "sample-feature")
    _complete_reviews(module, tmp_path, "sample-feature")
    _write_feature_test(tmp_path, "tests/unit/test_sample_feature.py", "sample-feature", "unit")

    result = module.validate_workflow(tmp_path, "sample-feature", run_commands=False)

    assert result.ok is False
    assert result.reason == "Missing required test categories for `sample-feature`: properties, validation."


def test_clear_removes_temporary_spec_review_files_and_state(tmp_path: Path) -> None:
    module = _load_validator()

    module.init_workflow(tmp_path, "sample-feature")

    message = module._clear_state(tmp_path, "sample-feature")

    assert message == "Cleared add-feature workflow state for `sample-feature`."
    assert not module._state_path(tmp_path).exists()
    assert not module._spec_path(tmp_path, "sample-feature").exists()
    for reviewer_name in module.REVIEWER_NAMES:
        assert not module._review_path(tmp_path, "sample-feature", reviewer_name).exists()
    assert not (tmp_path / ".tmp" / "add-feature" / "reviews").exists()


def test_validate_mark_passed_cleans_temporary_spec_review_files_and_state(tmp_path: Path) -> None:
    module = _load_validator()

    module.init_workflow(tmp_path, "sample-feature")
    _complete_spec(module, tmp_path, "sample-feature")
    _complete_reviews(module, tmp_path, "sample-feature")

    original_root = module.ROOT
    original_validate_workflow = module.validate_workflow
    try:
        module.ROOT = tmp_path

        def fake_validate_workflow(root: Path, feature_slug: str, run_commands: object):
            return module.ValidationResult(True, None, [])

        module.validate_workflow = fake_validate_workflow
        exit_code = module.main(["validate", "--slug", "sample-feature", "--mark-passed"])
    finally:
        module.ROOT = original_root
        module.validate_workflow = original_validate_workflow

    assert exit_code == 0
    assert not module._state_path(tmp_path).exists()
    assert not module._spec_path(tmp_path, "sample-feature").exists()
    for reviewer_name in module.REVIEWER_NAMES:
        assert not module._review_path(tmp_path, "sample-feature", reviewer_name).exists()


def test_validate_main_uses_checkpoint_mode_by_default(tmp_path: Path) -> None:
    module = _load_validator()

    module.init_workflow(tmp_path, "sample-feature")

    original_root = module.ROOT
    original_validate_workflow = module.validate_workflow
    called: dict[str, object] = {}
    try:
        module.ROOT = tmp_path

        def fake_validate_workflow(root: Path, feature_slug: str, *, run_commands: object):
            called["root"] = root
            called["feature_slug"] = feature_slug
            called["run_commands"] = run_commands
            return module.ValidationResult(True, None, [])

        module.validate_workflow = fake_validate_workflow
        exit_code = module.main(["validate", "--slug", "sample-feature"])
    finally:
        module.ROOT = original_root
        module.validate_workflow = original_validate_workflow

    assert exit_code == 0
    assert called == {
        "root": tmp_path,
        "feature_slug": "sample-feature",
        "run_commands": "checkpoint",
    }


def test_validate_main_uses_completion_mode_for_full_validation(tmp_path: Path) -> None:
    module = _load_validator()

    module.init_workflow(tmp_path, "sample-feature")

    original_root = module.ROOT
    original_validate_workflow = module.validate_workflow
    called: dict[str, object] = {}
    try:
        module.ROOT = tmp_path

        def fake_validate_workflow(root: Path, feature_slug: str, *, run_commands: object):
            called["root"] = root
            called["feature_slug"] = feature_slug
            called["run_commands"] = run_commands
            return module.ValidationResult(True, None, [])

        module.validate_workflow = fake_validate_workflow
        exit_code = module.main(["validate", "--slug", "sample-feature", "--full"])
    finally:
        module.ROOT = original_root
        module.validate_workflow = original_validate_workflow

    assert exit_code == 0
    assert called == {
        "root": tmp_path,
        "feature_slug": "sample-feature",
        "run_commands": "completion",
    }


def test_validate_static_checks_pass_with_complete_setup(tmp_path: Path) -> None:
    module = _load_validator()

    module.init_workflow(tmp_path, "sample-feature")
    _complete_spec(module, tmp_path, "sample-feature")
    _complete_reviews(module, tmp_path, "sample-feature")
    _write_feature_test(tmp_path, "tests/unit/test_sample_feature_unit.py", "sample-feature", "unit")
    _write_feature_test(
        tmp_path,
        "tests/integration/validation/test_sample_feature_validation.py",
        "sample-feature",
        "validation",
    )
    _write_feature_test(
        tmp_path,
        "tests/integration/properties/test_sample_feature_properties.py",
        "sample-feature",
        "properties",
    )

    result = module.validate_workflow(tmp_path, "sample-feature", run_commands=False)

    assert result.ok is True
    assert result.reason is None


def test_init_does_not_reset_active_workflow_baseline_or_allow_second_slug(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("base\n", encoding="utf-8")
    _git_commit_all(tmp_path, "base")

    module.init_workflow(tmp_path, "first-feature")
    first_state = module._load_state(tmp_path)
    assert first_state is not None

    module.init_workflow(tmp_path, "first-feature")
    second_state = module._load_state(tmp_path)
    assert second_state is not None
    assert second_state["baseline_changed_paths"] == first_state["baseline_changed_paths"]

    try:
        module.init_workflow(tmp_path, "second-feature")
    except SystemExit as exc:
        assert "already active" in str(exc)
    else:
        raise AssertionError("Expected init_workflow to reject a second active feature slug.")


def test_validate_requires_api_contract_when_public_api_changes(tmp_path: Path) -> None:
    module = _load_validator()

    module.init_workflow(tmp_path, "sample-feature")
    _complete_spec(module, tmp_path, "sample-feature", include_public_api_change=True)
    _complete_reviews(module, tmp_path, "sample-feature")
    _write_feature_test(tmp_path, "tests/unit/test_sample_feature_unit.py", "sample-feature", "unit")
    _write_feature_test(
        tmp_path,
        "tests/integration/validation/test_sample_feature_validation.py",
        "sample-feature",
        "validation",
    )
    _write_feature_test(
        tmp_path,
        "tests/integration/properties/test_sample_feature_properties.py",
        "sample-feature",
        "properties",
    )

    result = module.validate_workflow(tmp_path, "sample-feature", run_commands=False)

    assert result.ok is False
    assert result.reason == "Required test categories are too weak for this feature. Add: api_contract."


def test_validate_requires_changed_feature_tests_for_changed_behavior(tmp_path: Path) -> None:
    module = _load_validator()
    _init_git_repo(tmp_path)
    (tmp_path / "tests" / "unit").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "integration" / "validation").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "integration" / "properties").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)

    _write_feature_test(tmp_path, "tests/unit/test_sample_feature_unit.py", "sample-feature", "unit")
    _write_feature_test(
        tmp_path,
        "tests/integration/validation/test_sample_feature_validation.py",
        "sample-feature",
        "validation",
    )
    _write_feature_test(
        tmp_path,
        "tests/integration/properties/test_sample_feature_properties.py",
        "sample-feature",
        "properties",
    )
    (tmp_path / "src" / "engine.py").write_text("BASE = 1\n", encoding="utf-8")
    _git_commit_all(tmp_path, "base")

    module.init_workflow(tmp_path, "sample-feature")
    _complete_spec(module, tmp_path, "sample-feature")
    _complete_reviews(module, tmp_path, "sample-feature")
    (tmp_path / "src" / "engine.py").write_text("BASE = 2\n", encoding="utf-8")

    result = module.validate_workflow(tmp_path, "sample-feature", run_commands=False)

    assert result.ok is False
    assert result.reason == "Changed behavior has no changed feature-owned tests with the required pytest markers."


def test_init_migrates_legacy_public_spec_to_temporary_workflow_area(tmp_path: Path) -> None:
    module = _load_validator()
    legacy_spec_path = tmp_path / "specs" / "features" / "sample-feature.json"
    legacy_spec_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_spec_path.write_text(
        json.dumps(module._default_spec("sample-feature", "legacy request"), indent=2) + "\n",
        encoding="utf-8",
    )

    module.init_workflow(tmp_path, "sample-feature")

    assert not legacy_spec_path.exists()
    assert module._spec_path(tmp_path, "sample-feature").exists()
    payload = module._json_load(module._spec_path(tmp_path, "sample-feature"))
    assert payload["request_text"] == "legacy request"


def test_user_prompt_hook_blocks_second_active_feature_and_stop_hook_stops_repeated_loops(tmp_path: Path) -> None:
    module = _load_validator()
    module.init_workflow(tmp_path, "sample-feature")

    original_stdin = sys.stdin
    original_stdout = sys.stdout
    try:
        sys.stdin = io.StringIO(json.dumps({"prompt": "$add-feature add a thing"}))
        sys.stdout = io.StringIO()
        assert module._handle_user_prompt_hook(tmp_path) == 0
        user_prompt_output = json.loads(sys.stdout.getvalue())
        assert user_prompt_output["decision"] == "block"

        sys.stdin = io.StringIO(json.dumps({"stop_hook_active": True}))
        sys.stdout = io.StringIO()
        assert module._handle_stop_hook(tmp_path) == 0
        stop_output = json.loads(sys.stdout.getvalue())
        assert stop_output["continue"] is False
    finally:
        sys.stdin = original_stdin
        sys.stdout = original_stdout
