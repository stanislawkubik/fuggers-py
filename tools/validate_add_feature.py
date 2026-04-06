from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]

REVIEWER_NAMES = ("fi_api_reviewer", "fi_finance_reviewer", "fi_diff_reviewer")
DEFAULT_REQUIRED_TEST_CATEGORIES = ["unit", "validation", "properties"]
ALLOWED_TEST_CATEGORIES = {
    "unit": Path("tests/unit"),
    "validation": Path("tests/integration/validation"),
    "properties": Path("tests/integration/properties"),
    "workflow": Path("tests/integration/workflows"),
    "api_contract": Path("tests/contracts/api"),
    "architecture_contract": Path("tests/contracts/architecture"),
    "docs_smoke": Path("tests/contracts/docs"),
    "examples_smoke": Path("tests/integration/examples"),
}
REQUIRED_SPEC_FIELDS = (
    "summary",
    "public_api",
    "formulas_or_rules",
    "conventions",
    "accepted_inputs",
    "rejected_inputs",
    "edge_cases",
    "invariants",
    "numerical_tolerance",
    "required_test_categories",
)
REQUIRED_REVIEW_SECTIONS = (
    "## Findings",
    "## Missing tests",
    "## Open questions",
    "## Verdict",
)
WORKFLOW_REQUIRED_PREFIXES = (
    "src/fuggers_py/calc/",
    "src/fuggers_py/portfolio/",
)
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FEATURE_SLUG_MARKER_RE = re.compile(r"@pytest\.mark\.feature_slug\((?P<quote>['\"])(?P<slug>[^'\"]+)(?P=quote)\)")
FEATURE_CATEGORY_MARKER_RE = re.compile(
    r"@pytest\.mark\.feature_category\((?P<quote>['\"])(?P<category>[^'\"]+)(?P=quote)\)"
)
VERDICT_RE = re.compile(r"^-\s+(approve|approve with changes|block)\s*$", flags=re.IGNORECASE | re.MULTILINE)
ADD_FEATURE_TRIGGER_RE = re.compile(r"(?<!\w)\$add-feature\b")
VALIDATION_COMMAND_MODES = {"none", "checkpoint", "completion"}
ValidationCommandMode = Literal["none", "checkpoint", "completion"]


@dataclass(frozen=True, slots=True)
class ValidationResult:
    ok: bool
    reason: str | None
    details: list[str]


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _spec_dir(root: Path) -> Path:
    return _workflow_tmp_dir(root) / "specs"


def _legacy_spec_dir(root: Path) -> Path:
    return root / "specs" / "features"


def _workflow_tmp_dir(root: Path) -> Path:
    return root / ".tmp" / "add-feature"


def _review_dir(root: Path) -> Path:
    return _workflow_tmp_dir(root) / "reviews"


def _state_path(root: Path) -> Path:
    return _workflow_tmp_dir(root) / ".state.json"


def _spec_path(root: Path, feature_slug: str) -> Path:
    return _spec_dir(root) / f"{feature_slug}.json"


def _legacy_spec_path(root: Path, feature_slug: str) -> Path:
    return _legacy_spec_dir(root) / f"{feature_slug}.json"


def _review_path(root: Path, feature_slug: str, reviewer_name: str) -> Path:
    return _review_dir(root) / f"{feature_slug}.{reviewer_name}.md"


def _cleanup_empty_dirs(*directories: Path) -> None:
    for directory in directories:
        try:
            directory.rmdir()
        except OSError:
            pass


def _resolve_spec_path(root: Path, feature_slug: str, *, for_write: bool) -> Path:
    spec_path = _spec_path(root, feature_slug)
    legacy_path = _legacy_spec_path(root, feature_slug)
    if spec_path.exists():
        return spec_path
    if legacy_path.exists():
        if for_write:
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            spec_path.write_text(legacy_path.read_text(encoding="utf-8"), encoding="utf-8")
            legacy_path.unlink(missing_ok=True)
            _cleanup_empty_dirs(_legacy_spec_dir(root), root / "specs")
            return spec_path
        return legacy_path
    return spec_path


def _cleanup_temp_workflow_files(root: Path, feature_slug: str) -> None:
    for reviewer_name in REVIEWER_NAMES:
        _review_path(root, feature_slug, reviewer_name).unlink(missing_ok=True)
    _spec_path(root, feature_slug).unlink(missing_ok=True)
    _legacy_spec_path(root, feature_slug).unlink(missing_ok=True)
    _state_path(root).unlink(missing_ok=True)
    _cleanup_empty_dirs(
        _spec_dir(root),
        _review_dir(root),
        _workflow_tmp_dir(root),
        root / ".tmp",
        _legacy_spec_dir(root),
        root / "specs",
    )


def _validate_slug(feature_slug: str) -> None:
    if not SLUG_RE.fullmatch(feature_slug):
        raise SystemExit(
            "Feature slug must be lower-case kebab-case, for example `fixed-rate-oas`."
        )


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _json_load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _default_spec(feature_slug: str, request_text: str) -> dict[str, Any]:
    return {
        "feature_slug": feature_slug,
        "request_text": request_text,
        "summary": {
            "problem": "",
            "outcome": "",
        },
        "public_api": {
            "new_symbols": [],
            "changed_symbols": [],
            "backward_compatibility": "",
            "docs_examples_to_update": [],
        },
        "formulas_or_rules": [],
        "conventions": [],
        "accepted_inputs": [],
        "rejected_inputs": [],
        "edge_cases": [],
        "invariants": [],
        "numerical_tolerance": {
            "absolute": "",
            "relative": "",
            "notes": "",
        },
        "required_test_categories": list(DEFAULT_REQUIRED_TEST_CATEGORIES),
        "reviewers": {reviewer_name: "pending" for reviewer_name in REVIEWER_NAMES},
        "workflow_state": "draft",
    }


def _default_review_text(feature_slug: str, reviewer_name: str) -> str:
    return (
        f"# {reviewer_name}\n"
        f"Feature: {feature_slug}\n"
        "Status: pending\n\n"
        "## Findings\n"
        "- Pending review.\n\n"
        "## Missing tests\n"
        "- Pending review.\n\n"
        "## Open questions\n"
        "- Pending review.\n\n"
        "## Verdict\n"
        "- pending\n"
    )


def _run_shell(root: Path, command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def _git_output(root: Path, command: list[str]) -> list[str]:
    completed = _run_shell(root, command)
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _git_available(root: Path) -> bool:
    completed = _run_shell(root, ["git", "rev-parse", "--show-toplevel"])
    return completed.returncode == 0


def _current_changed_paths(root: Path) -> set[str]:
    if not _git_available(root):
        return set()
    changed = set(_git_output(root, ["git", "diff", "--name-only", "--relative", "HEAD"]))
    changed.update(_git_output(root, ["git", "diff", "--name-only", "--relative", "--cached", "HEAD"]))
    changed.update(_git_output(root, ["git", "ls-files", "--others", "--exclude-standard"]))
    return changed


def _load_state(root: Path) -> dict[str, Any] | None:
    path = _state_path(root)
    if not path.exists():
        return None
    return _json_load(path)


def _save_state(root: Path, payload: dict[str, Any]) -> None:
    _json_dump(_state_path(root), payload)


def init_workflow(root: Path, feature_slug: str, request_text: str = "") -> None:
    _validate_slug(feature_slug)
    existing_state = _load_state(root)
    if existing_state is not None and existing_state.get("passed") is not True:
        active_slug = str(existing_state.get("feature_slug", "")).strip()
        if active_slug and active_slug != feature_slug:
            raise SystemExit(
                "Another add-feature workflow is already active for "
                f"`{active_slug}`. Finish it or clear it with "
                f"`python tools/validate_add_feature.py clear --slug {active_slug}` first."
            )

    spec_path = _resolve_spec_path(root, feature_slug, for_write=True)
    review_dir = _review_dir(root)
    review_dir.mkdir(parents=True, exist_ok=True)
    _spec_dir(root).mkdir(parents=True, exist_ok=True)
    if not spec_path.exists():
        _json_dump(spec_path, _default_spec(feature_slug, request_text))

    for reviewer_name in REVIEWER_NAMES:
        review_path = _review_path(root, feature_slug, reviewer_name)
        if not review_path.exists():
            review_path.write_text(_default_review_text(feature_slug, reviewer_name), encoding="utf-8")

    if existing_state is not None and str(existing_state.get("feature_slug", "")).strip() == feature_slug:
        state = existing_state
        if request_text and not state.get("request_text"):
            state["request_text"] = request_text
    else:
        state = {
            "workflow_name": "add-feature",
            "feature_slug": feature_slug,
            "request_text": request_text,
            "created_at": _now_iso(),
            "baseline_changed_paths": sorted(_current_changed_paths(root)),
            "passed": False,
            "last_validation_ok": False,
            "last_validation_reason": (
                f"Finish the {feature_slug} workflow and run "
                "`python tools/validate_add_feature.py validate --mark-passed`."
            ),
        }
    _save_state(root, state)
    _update_spec_status(root, feature_slug, workflow_state="draft")


def _is_meaningful(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    return True


def _require_non_empty_string(value: Any, field_name: str) -> str | None:
    if isinstance(value, str) and value.strip():
        return None
    return f"Feature spec field `{field_name}` must be a non-empty string."


def _require_list_of_non_empty_strings(value: Any, field_name: str) -> str | None:
    if not isinstance(value, list) or not value:
        return f"Feature spec field `{field_name}` must be a non-empty list."
    if any(not isinstance(item, str) or not item.strip() for item in value):
        return f"Feature spec field `{field_name}` must contain only non-empty strings."
    return None


def _review_complete(text: str, feature_slug: str) -> bool:
    has_feature = f"Feature: {feature_slug}" in text
    has_complete = re.search(r"^Status:\s*complete\s*$", text, flags=re.IGNORECASE | re.MULTILINE)
    if not has_feature or not has_complete:
        return False
    if "Pending review" in text:
        return False
    if any(section not in text for section in REQUIRED_REVIEW_SECTIONS):
        return False
    return bool(VERDICT_RE.search(text))


def _spec_shape_errors(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    summary = spec.get("summary")
    if not isinstance(summary, dict):
        errors.append("Feature spec field `summary` must be an object with `problem` and `outcome`.")
    else:
        for key in ("problem", "outcome"):
            error = _require_non_empty_string(summary.get(key), f"summary.{key}")
            if error is not None:
                errors.append(error)

    public_api = spec.get("public_api")
    if not isinstance(public_api, dict):
        errors.append(
            "Feature spec field `public_api` must be an object with `new_symbols`, `changed_symbols`, "
            "`backward_compatibility`, and `docs_examples_to_update`."
        )
    else:
        for key in ("new_symbols", "changed_symbols", "docs_examples_to_update"):
            value = public_api.get(key)
            if not isinstance(value, list):
                errors.append(f"Feature spec field `public_api.{key}` must be a list.")
            elif any(not isinstance(item, str) or not item.strip() for item in value):
                errors.append(f"Feature spec field `public_api.{key}` must contain only non-empty strings.")
        error = _require_non_empty_string(public_api.get("backward_compatibility"), "public_api.backward_compatibility")
        if error is not None:
            errors.append(error)

    for key in (
        "formulas_or_rules",
        "conventions",
        "accepted_inputs",
        "rejected_inputs",
        "edge_cases",
        "invariants",
    ):
        error = _require_list_of_non_empty_strings(spec.get(key), key)
        if error is not None:
            errors.append(error)

    numerical_tolerance = spec.get("numerical_tolerance")
    if not isinstance(numerical_tolerance, dict):
        errors.append("Feature spec field `numerical_tolerance` must be an object.")
    else:
        for key in ("absolute", "relative"):
            error = _require_non_empty_string(numerical_tolerance.get(key), f"numerical_tolerance.{key}")
            if error is not None:
                errors.append(error)
        notes = numerical_tolerance.get("notes")
        if notes is not None and not isinstance(notes, str):
            errors.append("Feature spec field `numerical_tolerance.notes` must be a string when present.")

    categories = spec.get("required_test_categories")
    if not isinstance(categories, list) or not categories:
        errors.append("Feature spec field `required_test_categories` must be a non-empty list.")
    elif any(not isinstance(item, str) or not item.strip() for item in categories):
        errors.append("Feature spec field `required_test_categories` must contain only non-empty strings.")

    return errors


def _conditional_required_categories(spec: dict[str, Any], changed_paths: set[str]) -> set[str]:
    required: set[str] = set(DEFAULT_REQUIRED_TEST_CATEGORIES)
    public_api = spec.get("public_api", {})
    if isinstance(public_api, dict):
        if public_api.get("new_symbols") or public_api.get("changed_symbols"):
            required.add("api_contract")
        for path_text in public_api.get("docs_examples_to_update", []):
            if path_text == "README.md" or str(path_text).startswith("docs/"):
                required.add("docs_smoke")
            if str(path_text).startswith("examples/"):
                required.add("examples_smoke")
    if any(path_text == "README.md" or path_text.startswith("docs/") for path_text in changed_paths):
        required.add("docs_smoke")
    if any(path_text.startswith("examples/") for path_text in changed_paths):
        required.add("examples_smoke")
    if any(path_text.startswith(prefix) for prefix in WORKFLOW_REQUIRED_PREFIXES for path_text in changed_paths):
        required.add("workflow")
    return required


def _feature_test_inventory(root: Path, feature_slug: str) -> dict[str, set[str]]:
    inventory: dict[str, set[str]] = {}
    for path in sorted((root / "tests").rglob("test_*.py")):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        slugs = {match.group("slug") for match in FEATURE_SLUG_MARKER_RE.finditer(text)}
        if feature_slug not in slugs:
            continue
        categories = {match.group("category") for match in FEATURE_CATEGORY_MARKER_RE.finditer(text)}
        inventory[str(path.relative_to(root))] = categories
    return inventory


def _path_matches_category(path_text: str, category: str) -> bool:
    expected_root = ALLOWED_TEST_CATEGORIES[category]
    return Path(path_text).is_relative_to(expected_root)


def _feature_owned_paths(root: Path, state: dict[str, Any] | None) -> set[str]:
    current = _current_changed_paths(root)
    if state is None:
        return current
    baseline = set(state.get("baseline_changed_paths", []))
    return current - baseline


def _needs_behavior_tests(changed_paths: set[str]) -> bool:
    for path_text in changed_paths:
        if path_text == "pyproject.toml":
            return True
        if path_text.startswith("src/") or path_text.startswith("tools/"):
            return True
    return False


def _update_spec_status(root: Path, feature_slug: str, *, workflow_state: str) -> None:
    spec_path = _resolve_spec_path(root, feature_slug, for_write=True)
    if not spec_path.exists():
        return
    spec = _json_load(spec_path)
    spec["workflow_state"] = workflow_state
    reviewers = spec.setdefault("reviewers", {})
    for reviewer_name in REVIEWER_NAMES:
        review_path = _review_path(root, feature_slug, reviewer_name)
        if review_path.exists() and _review_complete(review_path.read_text(encoding="utf-8"), feature_slug):
            reviewers[reviewer_name] = "complete"
        else:
            reviewers[reviewer_name] = "pending"
    _json_dump(spec_path, spec)


def _checkpoint_validation_commands(feature_test_files: list[str]) -> list[list[str]]:
    commands: list[list[str]] = []
    if feature_test_files:
        commands.append(["pytest", "-q", *feature_test_files])
    return commands


def _completion_validation_commands(
    required_categories: list[str],
    changed_paths: set[str],
) -> list[list[str]]:
    commands: list[list[str]] = []
    for category in required_categories:
        if category == "unit":
            commands.append(["pytest", "-q", "tests/unit"])
        elif category == "validation":
            commands.append(["pytest", "-q", "tests/integration/validation"])
        elif category == "properties":
            commands.append(["pytest", "-q", "tests/integration/properties"])
        elif category == "workflow":
            commands.append(["pytest", "-q", "tests/integration/workflows"])
        elif category == "api_contract":
            commands.append(["pytest", "-q", "tests/contracts/api"])
        elif category == "architecture_contract":
            commands.append(["pytest", "-q", "tests/contracts/architecture"])
        elif category == "docs_smoke":
            commands.append(["pytest", "-q", "tests/contracts/docs"])
        elif category == "examples_smoke":
            commands.append(
                [
                    "pytest",
                    "-q",
                    "tests/integration/examples/test_examples_smoke.py",
                    "tests/integration/examples/test_examples_refactor_policy.py",
                ]
            )

    commands.extend(
        [
            [
                "ruff",
                "check",
                "src/fuggers_py",
                "tools/source_coverage.py",
                "tests/contracts/api/test_optional_dependencies.py",
                "typecheck",
                "tools/run_release_ruff.py",
                "tools/packaging",
                "tools/validate_add_feature.py",
            ],
            [sys.executable, "tools/run_release_ruff.py"],
            ["mypy"],
        ]
    )

    docs_changed = any(path.startswith("docs/") for path in changed_paths) or "README.md" in changed_paths
    if "docs_smoke" in required_categories or docs_changed:
        commands.append([sys.executable, "-m", "sphinx", "-W", "--keep-going", "-b", "html", "docs", "docs/_build/html"])

    return commands


def _validation_commands(
    feature_test_files: list[str],
    required_categories: list[str],
    changed_paths: set[str],
    *,
    command_mode: ValidationCommandMode,
) -> list[list[str]]:
    commands: list[list[str]] = []
    if command_mode in {"checkpoint", "completion"}:
        commands.extend(_checkpoint_validation_commands(feature_test_files))
    if command_mode == "completion":
        commands.extend(_completion_validation_commands(required_categories, changed_paths))
    return commands


def _normalize_command_mode(run_commands: bool | ValidationCommandMode) -> ValidationCommandMode:
    if run_commands is True:
        return "completion"
    if run_commands is False:
        return "none"
    if run_commands not in VALIDATION_COMMAND_MODES:
        raise ValueError(f"Unsupported validation command mode: {run_commands}")
    return run_commands


def validate_workflow(
    root: Path,
    feature_slug: str,
    *,
    run_commands: bool | ValidationCommandMode,
) -> ValidationResult:
    command_mode = _normalize_command_mode(run_commands)
    spec_path = _resolve_spec_path(root, feature_slug, for_write=False)
    if not spec_path.exists():
        return ValidationResult(False, f"Missing feature spec: {spec_path.relative_to(root)}", [])

    try:
        spec = _json_load(spec_path)
    except json.JSONDecodeError as exc:
        return ValidationResult(False, f"Feature spec is not valid JSON: {exc}", [])

    details: list[str] = []
    for field_name in REQUIRED_SPEC_FIELDS:
        if field_name not in spec:
            return ValidationResult(False, f"Feature spec is missing `{field_name}`.", details)
        if not _is_meaningful(spec[field_name]):
            return ValidationResult(False, f"Feature spec field `{field_name}` is still empty.", details)

    shape_errors = _spec_shape_errors(spec)
    if shape_errors:
        return ValidationResult(False, shape_errors[0], details)

    if spec.get("feature_slug") != feature_slug:
        return ValidationResult(False, "Feature spec slug does not match the active workflow slug.", details)

    required_categories = list(spec.get("required_test_categories", []))
    invalid_categories = [name for name in required_categories if name not in ALLOWED_TEST_CATEGORIES]
    if invalid_categories:
        return ValidationResult(
            False,
            f"Feature spec lists unsupported test categories: {', '.join(sorted(invalid_categories))}.",
            details,
        )

    changed_paths = _feature_owned_paths(root, _load_state(root))
    missing_conditional_categories = sorted(_conditional_required_categories(spec, changed_paths) - set(required_categories))
    if missing_conditional_categories:
        return ValidationResult(
            False,
            "Required test categories are too weak for this feature. Add: "
            + ", ".join(missing_conditional_categories)
            + ".",
            details,
        )

    for reviewer_name in REVIEWER_NAMES:
        review_path = _review_path(root, feature_slug, reviewer_name)
        if not review_path.exists():
            return ValidationResult(False, f"Missing reviewer output: {review_path.relative_to(root)}", details)
        if not _review_complete(review_path.read_text(encoding="utf-8"), feature_slug):
            return ValidationResult(
                False,
                f"Reviewer output is still pending: {review_path.relative_to(root)}",
                details,
            )

    inventory = _feature_test_inventory(root, feature_slug)
    if not inventory:
        return ValidationResult(
            False,
            f"No feature-owned pytest files found for slug `{feature_slug}`.",
            details,
        )

    categories_present: dict[str, list[str]] = {category: [] for category in ALLOWED_TEST_CATEGORIES}
    for path_text, categories in inventory.items():
        if not categories:
            return ValidationResult(
                False,
                f"Feature-owned test file lacks `feature_category` marker: {path_text}",
                details,
            )
        for category in categories:
            if category not in ALLOWED_TEST_CATEGORIES:
                return ValidationResult(
                    False,
                    f"Feature-owned test file uses unsupported category `{category}`: {path_text}",
                    details,
                )
            if not _path_matches_category(path_text, category):
                expected_root = ALLOWED_TEST_CATEGORIES[category]
                return ValidationResult(
                    False,
                    f"Feature-owned test file {path_text} does not live under {expected_root.as_posix()} for category `{category}`.",
                    details,
                )
            categories_present[category].append(path_text)

    missing_categories = [category for category in required_categories if not categories_present[category]]
    if missing_categories:
        return ValidationResult(
            False,
            f"Missing required test categories for `{feature_slug}`: {', '.join(sorted(missing_categories))}.",
            details,
        )

    changed_feature_test_paths = {path_text for path_text in inventory if path_text in changed_paths}
    if _needs_behavior_tests(changed_paths) and not changed_feature_test_paths:
        return ValidationResult(
            False,
            "Changed behavior has no changed feature-owned tests with the required pytest markers.",
            details,
        )

    changed_categories_present: dict[str, list[str]] = {category: [] for category in ALLOWED_TEST_CATEGORIES}
    for path_text in changed_feature_test_paths:
        for category in inventory[path_text]:
            changed_categories_present[category].append(path_text)
    missing_changed_categories = [category for category in required_categories if not changed_categories_present[category]]
    if _needs_behavior_tests(changed_paths) and missing_changed_categories:
        return ValidationResult(
            False,
            f"Required test categories are not represented in changed feature-owned tests: {', '.join(sorted(missing_changed_categories))}.",
            details,
        )

    if command_mode == "none":
        return ValidationResult(True, None, details)

    feature_test_files = sorted(inventory)
    for command in _validation_commands(
        feature_test_files,
        required_categories,
        changed_paths,
        command_mode=command_mode,
    ):
        completed = _run_shell(root, command)
        if completed.returncode != 0:
            joined = " ".join(command)
            stderr = completed.stderr.strip()
            stdout = completed.stdout.strip()
            snippet = stderr or stdout or "No command output captured."
            snippet = snippet.splitlines()[0]
            return ValidationResult(False, f"Validation command failed: `{joined}`. {snippet}", details)

    return ValidationResult(True, None, details)


def _resolve_feature_slug(root: Path, explicit_slug: str | None) -> str:
    state = _load_state(root)
    if explicit_slug is not None:
        _validate_slug(explicit_slug)
        if state is not None and state.get("passed") is not True:
            active_slug = str(state.get("feature_slug", "")).strip()
            if active_slug and active_slug != explicit_slug:
                raise SystemExit(
                    "Active add-feature workflow slug does not match the requested slug. "
                    f"Active: `{active_slug}`. Requested: `{explicit_slug}`."
                )
        return explicit_slug
    if state is None or not state.get("feature_slug"):
        raise SystemExit("No active add-feature workflow state found. Run `init --slug <feature-slug>` first.")
    return str(state["feature_slug"])


def _mark_state(
    root: Path,
    *,
    feature_slug: str,
    ok: bool,
    reason: str | None,
    passed: bool,
) -> None:
    state = _load_state(root) or {
        "workflow_name": "add-feature",
        "feature_slug": feature_slug,
        "created_at": _now_iso(),
        "baseline_changed_paths": sorted(_current_changed_paths(root)),
    }
    state["feature_slug"] = feature_slug
    state["last_validation_ok"] = ok
    state["last_validation_reason"] = reason
    state["last_validated_at"] = _now_iso()
    state["passed"] = passed
    _save_state(root, state)


def _status_message(root: Path, feature_slug: str | None = None) -> str:
    state = _load_state(root)
    if state is None:
        return "No active add-feature workflow state."
    active_slug = str(state.get("feature_slug", "")).strip()
    if feature_slug is not None and active_slug and active_slug != feature_slug:
        return f"Active add-feature workflow slug is `{active_slug}`, not `{feature_slug}`."
    if state.get("passed") is True:
        return f"Add-feature workflow `{active_slug}` is marked passed."
    reason = state.get("last_validation_reason")
    if isinstance(reason, str) and reason.strip():
        return reason
    return f"Add-feature workflow `{active_slug}` is active but not yet passed."


def _clear_state(root: Path, feature_slug: str | None) -> str:
    state = _load_state(root)
    if state is None:
        return "No active add-feature workflow state to clear."
    active_slug = str(state.get("feature_slug", "")).strip()
    if feature_slug is not None and active_slug and active_slug != feature_slug:
        raise SystemExit(f"Active add-feature workflow slug is `{active_slug}`, not `{feature_slug}`.")
    if active_slug:
        _update_spec_status(root, active_slug, workflow_state="cleared")
        _cleanup_temp_workflow_files(root, active_slug)
    else:
        _state_path(root).unlink(missing_ok=True)
    return f"Cleared add-feature workflow state for `{active_slug}`."


def _handle_user_prompt_hook(root: Path) -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        payload = {}

    prompt = str(payload.get("prompt", ""))
    if not ADD_FEATURE_TRIGGER_RE.search(prompt):
        return 0

    state = _load_state(root)
    if state is not None and state.get("passed") is not True:
        active_slug = str(state.get("feature_slug", "")).strip()
        print(
            json.dumps(
                {
                    "decision": "block",
                    "reason": (
                        f"An add-feature workflow for `{active_slug}` is already active. "
                        f"Finish it with `python tools/validate_add_feature.py validate --mark-passed` "
                        f"or clear it with `python tools/validate_add_feature.py clear --slug {active_slug}` "
                        "before starting another one."
                    ),
                }
            )
        )
        return 0

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": (
                        "This prompt uses the repo-local `$add-feature` trigger. Use the `add-feature` skill, "
                        "derive a kebab-case slug, run `python tools/validate_add_feature.py init --slug <feature-slug>` "
                        "before editing, complete the machine-readable spec, run `fi_api_reviewer` and "
                        "`fi_finance_reviewer` before implementation, run `fi_diff_reviewer` after the diff exists, "
                        "and do not finish until `python tools/validate_add_feature.py validate --mark-passed` passes."
                    ),
                }
            }
        )
    )
    return 0


def _handle_stop_hook(root: Path) -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}

    state = _load_state(root)
    if state is None or state.get("workflow_name") != "add-feature":
        return 0
    if state.get("passed") is True:
        return 0

    feature_slug = str(state.get("feature_slug", "")).strip()
    stop_hook_active = bool(payload.get("stop_hook_active"))
    if not feature_slug:
        message = (
            "The add-feature workflow state is missing `feature_slug`. "
            "Re-run `python tools/validate_add_feature.py init --slug <feature-slug>`."
        )
        if stop_hook_active:
            print(json.dumps({"continue": False, "stopReason": message, "systemMessage": message}))
        else:
            print(json.dumps({"decision": "block", "reason": message}))
        return 0

    result = validate_workflow(root, feature_slug, run_commands=False)
    if not result.ok:
        message = result.reason
    else:
        message = (
            f"Finish the add-feature workflow for `{feature_slug}` by running "
            "`python tools/validate_add_feature.py validate --mark-passed`. "
            f"If this workflow is stale, clear it with `python tools/validate_add_feature.py clear --slug {feature_slug}`."
        )

    assert message is not None
    if stop_hook_active:
        print(json.dumps({"continue": False, "stopReason": message, "systemMessage": message}))
        return 0

    if not result.ok:
        print(json.dumps({"decision": "block", "reason": message}))
        return 0

    print(json.dumps({"decision": "block", "reason": message}))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validator for the repo-local $add-feature workflow.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init",
        help="Initialize add-feature state, temporary spec, and temporary reviewer files.",
    )
    init_parser.add_argument("--slug", required=True, help="Feature slug in lower-case kebab-case.")
    init_parser.add_argument("--request-text", default="", help="Optional raw user request text.")

    validate_parser = subparsers.add_parser("validate", help="Validate the active add-feature workflow.")
    validate_parser.add_argument("--slug", default=None, help="Optional feature slug override.")
    validate_parser.add_argument(
        "--full",
        action="store_true",
        help="Run the full repo-wide validation command bundle without marking the workflow passed.",
    )
    validate_parser.add_argument(
        "--mark-passed",
        action="store_true",
        help="Mark the workflow passed when validation succeeds.",
    )

    status_parser = subparsers.add_parser("status", help="Show the current add-feature workflow state.")
    status_parser.add_argument("--slug", default=None, help="Optional feature slug.")

    clear_parser = subparsers.add_parser("clear", help="Clear the current add-feature workflow state.")
    clear_parser.add_argument("--slug", default=None, help="Optional feature slug safeguard.")

    subparsers.add_parser("user-prompt-hook", help="Hook entrypoint used by Codex UserPromptSubmit hooks.")
    subparsers.add_parser("stop-hook", help="Hook entrypoint used by Codex Stop hooks.")

    args = parser.parse_args(argv)

    if args.command == "init":
        init_workflow(ROOT, args.slug, request_text=args.request_text)
        print(
            f"Initialized add-feature workflow for `{args.slug}`. "
            f"Fill {_spec_path(ROOT, args.slug).relative_to(ROOT)} and temporary reviewer outputs before implementation."
        )
        return 0

    if args.command == "stop-hook":
        return _handle_stop_hook(ROOT)

    if args.command == "user-prompt-hook":
        return _handle_user_prompt_hook(ROOT)

    if args.command == "status":
        print(_status_message(ROOT, feature_slug=args.slug))
        return 0

    if args.command == "clear":
        print(_clear_state(ROOT, feature_slug=args.slug))
        return 0

    feature_slug = _resolve_feature_slug(ROOT, args.slug)
    command_mode: ValidationCommandMode = "completion" if args.mark_passed or args.full else "checkpoint"
    result = validate_workflow(ROOT, feature_slug, run_commands=command_mode)
    if not result.ok:
        _mark_state(ROOT, feature_slug=feature_slug, ok=False, reason=result.reason, passed=False)
        assert result.reason is not None
        print(result.reason)
        return 1

    passed = bool(args.mark_passed)
    if passed:
        reason = None
    elif args.full:
        reason = (
            f"Full validation passed for `{feature_slug}`. Run "
            "`python tools/validate_add_feature.py validate --mark-passed` to record completion."
        )
    else:
        reason = (
            f"Checkpoint validation passed for `{feature_slug}`. Run "
            "`python tools/validate_add_feature.py validate --full` for the repo-wide gate or "
            "`python tools/validate_add_feature.py validate --mark-passed` to record completion."
        )
    _mark_state(ROOT, feature_slug=feature_slug, ok=True, reason=reason, passed=passed)
    _update_spec_status(ROOT, feature_slug, workflow_state="passed" if passed else "validated")
    if passed:
        _cleanup_temp_workflow_files(ROOT, feature_slug)
        print(f"PASS: add-feature workflow is complete for `{feature_slug}`.")
    else:
        print(reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
