from __future__ import annotations

import argparse
import ast
import importlib
import importlib.util
import hashlib
import inspect
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]

WORKFLOW_NAME = "public-api-refactor"
TARGET_PUBLIC_MODULES = (
    "curves",
    "vol_surfaces",
    "bonds",
    "rates",
    "inflation",
    "credit",
    "funding",
    "portfolio",
)
CANONICAL_PUBLIC_PACKAGES = ("fuggers_py", *(f"fuggers_py.{module_name}" for module_name in TARGET_PUBLIC_MODULES))
LEGACY_PACKAGE_ROOTS = ("market", "products", "pricers", "measures", "reference", "calc", "adapters")
DRAIN_BUCKETS = (
    "_market",
    "_products",
    "_pricers",
    "_measures",
    "_reference",
    "_calc",
    "_adapters",
    "_curves_impl",
    "_vol_surfaces_impl",
)
RELEVANT_PREFIXES = (
    "src/fuggers_py/",
    "docs/",
    "examples/",
    "tests/contracts/",
    "tools/",
    "refactor/",
    ".codex/",
)
RELEVANT_FILES = {"README.md", "pyproject.toml"}
USER_FACING_PREFIXES = ("docs/", "examples/", "tests/contracts/", "refactor/")
USER_FACING_FILES = {"README.md"}
CURRENT_INVENTORY_RELATIVE_PATH = "refactor/PUBLIC_API_CURRENT_INVENTORY.json"
EXPORT_MANIFEST_RELATIVE_PATH = "refactor/PUBLIC_API_EXPORT_MANIFEST.json"
LEGACY_DENYLIST_RELATIVE_PATH = "refactor/PUBLIC_API_LEGACY_DENYLIST.json"
MIGRATION_LEDGER_RELATIVE_PATH = "refactor/PUBLIC_API_MIGRATION_LEDGER.json"
STRUCTURE_MANIFEST_RELATIVE_PATH = "refactor/PUBLIC_API_STRUCTURE_MANIFEST.json"
DEPENDENCY_MANIFEST_RELATIVE_PATH = "refactor/PUBLIC_API_DEPENDENCY_MANIFEST.json"
TARGET_STATE_RELATIVE_PATH = "refactor/PUBLIC_API_TARGET_STATE.md"
REFACTOR_PLAN_RELATIVE_PATH = "refactor/PUBLIC_API_REFACTOR_PLAN.md"
LEGACY_IMPORT_REPLACEMENTS = {
    "fuggers_py.market.curves": "fuggers_py.curves",
    "fuggers_py.market.vol_surfaces": "fuggers_py.vol_surfaces",
    "fuggers_py.products.bonds": "fuggers_py.bonds",
    "fuggers_py.pricers.bonds": "fuggers_py.bonds",
    "fuggers_py.measures.yields": "fuggers_py.bonds",
    "fuggers_py.measures.spreads": "fuggers_py.bonds",
    "fuggers_py.measures.risk": "fuggers_py.bonds",
    "fuggers_py.measures.yas": "fuggers_py.bonds",
    "fuggers_py.products.rates": "fuggers_py.rates",
    "fuggers_py.pricers.rates": "fuggers_py.rates",
    "fuggers_py.market.indices": "fuggers_py.rates",
    "fuggers_py.reference.inflation": "fuggers_py.inflation",
    "fuggers_py.measures.inflation": "fuggers_py.inflation",
    "fuggers_py.products.credit": "fuggers_py.credit",
    "fuggers_py.pricers.credit": "fuggers_py.credit",
    "fuggers_py.measures.credit": "fuggers_py.credit",
    "fuggers_py.products.funding": "fuggers_py.funding",
    "fuggers_py.measures.funding": "fuggers_py.funding",
}
ROOT_SHARED_OWNER_OVERRIDES = {
    "Date": "fuggers_py._core",
    "Currency": "fuggers_py._core",
    "Frequency": "fuggers_py._core",
    "Compounding": "fuggers_py._core",
    "Price": "fuggers_py._core",
    "Yield": "fuggers_py._core",
    "Spread": "fuggers_py._core",
    "InstrumentId": "fuggers_py._core",
    "CurveId": "fuggers_py._core",
    "PortfolioId": "fuggers_py._core",
    "YearMonth": "fuggers_py._core",
    "DayCountConvention": "fuggers_py._core",
    "BusinessDayConvention": "fuggers_py._core",
    "Tenor": "fuggers_py._core",
    "CalendarId": "fuggers_py._core",
    "SettlementAdjustment": "fuggers_py._core",
    "YieldCalculationRules": "fuggers_py._core",
    "PayReceive": "fuggers_py._core",
    "OptionType": "fuggers_py._core",
    "BondType": "fuggers_py.bonds",
    "IssuerType": "fuggers_py.bonds",
    "USD_CPI_U_NSA": "fuggers_py.inflation",
    "IndexConventions": "fuggers_py.rates",
    "OvernightCompounding": "fuggers_py.rates",
}
PHASE1_MOVED_SYMBOL_FINAL_IMPORT_MODULES = {
    "Tenor": "fuggers_py._core",
    "CalendarId": "fuggers_py._core",
    "SettlementAdjustment": "fuggers_py._core",
    "YieldCalculationRules": "fuggers_py._core",
    "PayReceive": "fuggers_py._core",
    "OptionType": "fuggers_py._core",
    "BondType": "fuggers_py.bonds.types",
    "IssuerType": "fuggers_py.bonds.types",
}
PHASE1_MOVED_SYMBOLS = frozenset(PHASE1_MOVED_SYMBOL_FINAL_IMPORT_MODULES)
PHASE1_OLD_BUCKET_IMPORT_PREFIXES = (
    "fuggers_py._reference",
    "fuggers_py._products.rates",
)
CORE_SELF_CONTAINED_OWNER_RELATIVE_PATHS = frozenset(
    {
        "src/fuggers_py/_core/tenor.py",
        "src/fuggers_py/_core/calendar_id.py",
        "src/fuggers_py/_core/settlement_rules.py",
        "src/fuggers_py/_core/yield_calculation_rules.py",
    }
)
CORE_SELF_CONTAINED_FORBIDDEN_IMPORT_PREFIX = "fuggers_py._reference.bonds"
INTERNAL_SURVIVOR_TOP_LEVEL_PACKAGES = {"_core", "_math", "_runtime", "_storage"}
TRANSITION_BUCKET_TOP_LEVEL_PACKAGES = {
    "_adapters",
    "_calc",
    "_curves_impl",
    "_market",
    "_measures",
    "_pricers",
    "_products",
    "_reference",
    "_vol_surfaces_impl",
}
TARGET_DEPENDENCY_BASELINE = {
    "fuggers_py": {
        "fuggers_py._core",
        "fuggers_py.bonds",
        "fuggers_py.credit",
        "fuggers_py.curves",
        "fuggers_py.funding",
        "fuggers_py.inflation",
        "fuggers_py.portfolio",
        "fuggers_py.rates",
        "fuggers_py.vol_surfaces",
    },
    "fuggers_py.curves": {
        "fuggers_py._core",
        "fuggers_py._math",
        "fuggers_py.bonds",
        "fuggers_py.credit",
        "fuggers_py.funding",
        "fuggers_py.inflation",
        "fuggers_py.rates",
    },
    "fuggers_py.vol_surfaces": {
        "fuggers_py._core",
        "fuggers_py._math",
        "fuggers_py.bonds",
        "fuggers_py.credit",
        "fuggers_py.inflation",
        "fuggers_py.rates",
    },
    "fuggers_py.bonds": {
        "fuggers_py._core",
        "fuggers_py._math",
        "fuggers_py.curves",
        "fuggers_py.inflation",
        "fuggers_py.rates",
        "fuggers_py.vol_surfaces",
    },
    "fuggers_py.rates": {
        "fuggers_py._core",
        "fuggers_py._math",
        "fuggers_py.bonds",
        "fuggers_py.curves",
        "fuggers_py.vol_surfaces",
    },
    "fuggers_py.inflation": {
        "fuggers_py._core",
        "fuggers_py._math",
        "fuggers_py.bonds",
        "fuggers_py.curves",
        "fuggers_py.rates",
        "fuggers_py.vol_surfaces",
    },
    "fuggers_py.credit": {
        "fuggers_py._core",
        "fuggers_py._math",
        "fuggers_py.bonds",
        "fuggers_py.curves",
        "fuggers_py.rates",
        "fuggers_py.vol_surfaces",
    },
    "fuggers_py.funding": {
        "fuggers_py._core",
        "fuggers_py._math",
        "fuggers_py.bonds",
        "fuggers_py.curves",
        "fuggers_py.rates",
    },
    "fuggers_py.portfolio": {
        "fuggers_py._core",
        "fuggers_py._math",
        "fuggers_py._runtime",
        "fuggers_py._storage",
        "fuggers_py.bonds",
        "fuggers_py.credit",
        "fuggers_py.curves",
        "fuggers_py.funding",
        "fuggers_py.inflation",
        "fuggers_py.rates",
        "fuggers_py.vol_surfaces",
    },
}
FROZEN_PLANNING_ARTIFACT_PATHS = frozenset(
    {
        TARGET_STATE_RELATIVE_PATH,
        REFACTOR_PLAN_RELATIVE_PATH,
        CURRENT_INVENTORY_RELATIVE_PATH,
        EXPORT_MANIFEST_RELATIVE_PATH,
        LEGACY_DENYLIST_RELATIVE_PATH,
        MIGRATION_LEDGER_RELATIVE_PATH,
        STRUCTURE_MANIFEST_RELATIVE_PATH,
        DEPENDENCY_MANIFEST_RELATIVE_PATH,
    }
)
PLANNING_SUPPORT_PATHS = frozenset(
    {
        ".codex/hooks.json",
        ".codex/agents/public_api_reviewer.toml",
        ".gitignore",
        "tools/validate_public_api_refactor.py",
        "tests/contracts/tooling/test_public_api_current_inventory.py",
        "tests/contracts/tooling/test_public_api_phase1_slice2_controls.py",
        "tests/contracts/tooling/test_public_api_phase1_slice3_controls.py",
        "tests/contracts/tooling/test_public_api_refactor_validator.py",
    }
)
LEGACY_PUBLIC_PATH_REPLACEMENTS = {
    "src/fuggers_py/market/curves/": "curves",
    "src/fuggers_py/market/vol_surfaces/": "vol_surfaces",
    "src/fuggers_py/products/bonds/": "bonds",
    "src/fuggers_py/pricers/bonds/": "bonds",
    "src/fuggers_py/measures/yields/": "bonds",
    "src/fuggers_py/measures/spreads/": "bonds",
    "src/fuggers_py/measures/risk/": "bonds",
    "src/fuggers_py/measures/yas/": "bonds",
    "src/fuggers_py/products/rates/": "rates",
    "src/fuggers_py/pricers/rates/": "rates",
    "src/fuggers_py/market/indices/": "rates",
    "src/fuggers_py/reference/inflation/": "inflation",
    "src/fuggers_py/measures/inflation/": "inflation",
    "src/fuggers_py/products/credit/": "credit",
    "src/fuggers_py/pricers/credit/": "credit",
    "src/fuggers_py/measures/credit/": "credit",
    "src/fuggers_py/products/funding/": "funding",
    "src/fuggers_py/measures/funding/": "funding",
}
DRAIN_BUCKET_PATH_REPLACEMENTS = {
    "src/fuggers_py/_curves_impl/": "curves",
    "src/fuggers_py/_vol_surfaces_impl/": "vol_surfaces",
    "src/fuggers_py/_products/bonds/": "bonds",
    "src/fuggers_py/_pricers/bonds/": "bonds",
    "src/fuggers_py/_measures/yields/": "bonds",
    "src/fuggers_py/_measures/spreads/": "bonds",
    "src/fuggers_py/_measures/risk/": "bonds",
    "src/fuggers_py/_measures/yas/": "bonds",
    "src/fuggers_py/_products/rates/": "rates",
    "src/fuggers_py/_pricers/rates/": "rates",
    "src/fuggers_py/_market/indices/": "rates",
    "src/fuggers_py/_reference/inflation/": "inflation",
    "src/fuggers_py/_measures/inflation/": "inflation",
    "src/fuggers_py/_products/credit/": "credit",
    "src/fuggers_py/_pricers/credit/": "credit",
    "src/fuggers_py/_measures/credit/": "credit",
    "src/fuggers_py/_products/funding/": "funding",
    "src/fuggers_py/_measures/funding/": "funding",
}
WRAPPER_ALLOWED_FUNCTIONS = {"__getattr__", "__dir__"}
MAX_WRAPPER_NONEMPTY_LINES = 80
AUTO_ACTIVATE_TRIGGER_RE = re.compile(
    r"\b(public api refactor|public-api-refactor|target structure|new public structure|first-layer module|canonical import)\b",
    flags=re.IGNORECASE,
)
REVIEW_REQUIRED_SECTIONS = (
    "## Findings",
    "## Boundary risks",
    "## Missing deterministic checks",
    "## Verdict",
)
REVIEW_VERDICT_RE = re.compile(r"^-\s+(approve|approve with changes|block)\s*$", flags=re.IGNORECASE | re.MULTILINE)
ValidationCommandMode = Literal["none", "checkpoint", "completion"]


@dataclass(frozen=True, slots=True)
class ValidationResult:
    ok: bool
    reason: str | None
    details: list[str]
    fingerprint: str | None


def _workflow_dir(root: Path) -> Path:
    return root / ".tmp" / WORKFLOW_NAME


def _state_path(root: Path) -> Path:
    return _workflow_dir(root) / ".state.json"


def _default_review_path(root: Path) -> Path:
    return root / "artifacts" / "reviews" / "public_api_refactor.public_api_reviewer.md"


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _json_load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_shell(root: Path, command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)


def _git_output(root: Path, command: list[str]) -> list[str]:
    completed = _run_shell(root, command)
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _git_available(root: Path) -> bool:
    return _run_shell(root, ["git", "rev-parse", "--show-toplevel"]).returncode == 0


def _current_changed_paths(root: Path) -> set[str]:
    if not _git_available(root):
        return set()
    changed = set(_git_output(root, ["git", "diff", "--name-only", "--relative", "HEAD"]))
    changed.update(_git_output(root, ["git", "diff", "--name-only", "--relative", "--cached", "HEAD"]))
    changed.update(_git_output(root, ["git", "ls-files", "--others", "--exclude-standard"]))
    return changed


def _relevant_paths(paths: set[str]) -> set[str]:
    return {
        path_text
        for path_text in paths
        if "__pycache__/" not in path_text and not path_text.endswith(".pyc")
        if path_text in RELEVANT_FILES or any(path_text.startswith(prefix) for prefix in RELEVANT_PREFIXES)
    }


def _load_state(root: Path) -> dict[str, Any] | None:
    path = _state_path(root)
    if not path.exists():
        return None
    return _json_load(path)


def _save_state(root: Path, payload: dict[str, Any]) -> None:
    _json_dump(_state_path(root), payload)


def init_workflow(root: Path) -> dict[str, Any]:
    state = {
        "workflow_name": WORKFLOW_NAME,
        "created_at": _now_iso(),
        "active": True,
        "baseline_changed_paths": sorted(_relevant_paths(_current_changed_paths(root))),
        "last_validation_ok": False,
        "last_validation_reason": (
            "Run `python tools/validate_public_api_refactor.py complete --review "
            "artifacts/reviews/public_api_refactor.public_api_reviewer.md` after review."
        ),
        "last_validated_fingerprint": None,
        "last_validated_at": None,
        "last_reviewed_fingerprint": None,
        "last_reviewed_at": None,
        "last_completed_at": None,
    }
    _save_state(root, state)
    return state


def _ensure_state(root: Path, *, create_if_missing: bool = True) -> dict[str, Any] | None:
    state = _load_state(root)
    if state is None or state.get("workflow_name") != WORKFLOW_NAME:
        if not create_if_missing:
            return None
        return init_workflow(root)
    return state


def _workflow_is_active(state: dict[str, Any] | None) -> bool:
    return bool(state and state.get("workflow_name") == WORKFLOW_NAME and state.get("active") is True)


def deactivate_workflow(root: Path) -> str:
    state = _load_state(root)
    if state is None or state.get("workflow_name") != WORKFLOW_NAME:
        return "Public API refactor workflow is not active."
    state["active"] = False
    _save_state(root, state)
    return "Deactivated public API refactor workflow."


def _delta_paths(root: Path, state: dict[str, Any]) -> set[str]:
    baseline = set(state.get("baseline_changed_paths", []))
    current = _relevant_paths(_current_changed_paths(root))
    return current - baseline


def _fingerprint_for_paths(root: Path, relative_paths: set[str]) -> str | None:
    if not relative_paths:
        return None
    digest = hashlib.sha256()
    for relative_path in sorted(relative_paths):
        path = root / relative_path
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        if path.exists():
            digest.update(path.read_bytes())
        else:
            digest.update(b"<deleted>")
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def _normalize_command_mode(run_commands: bool | ValidationCommandMode) -> ValidationCommandMode:
    if run_commands is True:
        return "completion"
    if run_commands is False:
        return "none"
    if run_commands not in {"none", "checkpoint", "completion"}:
        raise ValueError(f"Unsupported validation command mode: {run_commands}")
    return run_commands


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _relative_path_text(root: Path, path: Path | str | None) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (root / candidate).resolve()
    else:
        candidate = candidate.resolve()
    try:
        return candidate.relative_to(root.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def _ensure_src_on_path(root: Path) -> None:
    src_path = str((root / "src").resolve())
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    importlib.invalidate_caches()


def _purge_loaded_package_modules(package_name: str) -> None:
    for module_name in list(sys.modules):
        if module_name == package_name or module_name.startswith(f"{package_name}."):
            del sys.modules[module_name]


def _module_name_for_path(root: Path, path: Path) -> str:
    relative = path.relative_to(root / "src").with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        if base is None:
            return None
        return f"{base}.{node.attr}"
    return None


def _static_string_sequence(node: ast.AST | None) -> list[str] | None:
    if node is None:
        return None
    try:
        value = ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return None
    if isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value):
        return list(value)
    return None


def _top_level_tree_info(tree: ast.Module) -> dict[str, object]:
    uses_import_module = False
    uses_getattr = False
    uses_dir = False
    routing_tables: list[str] = []
    static_all: list[str] | None = None

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if node.name == "__getattr__":
                uses_getattr = True
            elif node.name == "__dir__":
                uses_dir = True
        elif isinstance(node, ast.ImportFrom) and node.module == "importlib":
            if any(alias.name == "import_module" for alias in node.names):
                uses_import_module = True
        elif isinstance(node, ast.Import):
            if any(alias.name == "importlib" for alias in node.names):
                uses_import_module = True
        elif isinstance(node, ast.Assign):
            target_names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if "__all__" in target_names:
                static_all = _static_string_sequence(node.value)
            for name in target_names:
                if name != "__all__" and name.endswith("EXPORTS"):
                    routing_tables.append(name)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == "__all__":
                static_all = _static_string_sequence(node.value)
            elif node.target.id.endswith("EXPORTS"):
                routing_tables.append(node.target.id)

    return {
        "uses_import_module": uses_import_module,
        "uses___getattr__": uses_getattr,
        "uses___dir__": uses_dir,
        "routing_tables": sorted(set(routing_tables)),
        "static_all": static_all,
    }


def _runtime_all(root: Path, module_name: str) -> list[str]:
    _ensure_src_on_path(root)
    module = importlib.import_module(module_name)
    exports = getattr(module, "__all__", [])
    return [str(name) for name in exports]


def _load_runtime_module(root: Path, module_name: str):
    _ensure_src_on_path(root)
    return importlib.import_module(module_name)


def _runtime_symbol_kind(obj: object) -> str:
    if inspect.ismodule(obj):
        return "module"
    if inspect.isclass(obj):
        return "class"
    if inspect.isfunction(obj) or inspect.ismethod(obj) or inspect.isbuiltin(obj):
        return "function"
    if isinstance(obj, (str, int, float, complex, bool)):
        return "constant"
    return type(obj).__name__


def _runtime_export_record(root: Path, module_name: str, export_name: str) -> dict[str, object]:
    module = _load_runtime_module(root, module_name)
    try:
        obj = getattr(module, export_name)
    except AttributeError as exc:
        raise ValueError(
            f"{module_name} exports `{export_name}` in __all__ but does not bind it on plain attribute access."
        ) from exc
    resolved_module = obj.__name__ if inspect.ismodule(obj) else getattr(obj, "__module__", None)
    try:
        resolved_file = inspect.getsourcefile(obj)
    except TypeError:
        resolved_file = None
    return {
        "name": export_name,
        "kind": _runtime_symbol_kind(obj),
        "resolved_module": resolved_module,
        "resolved_file": _relative_path_text(root, resolved_file),
    }


def _assignment_target_names(node: ast.Assign | ast.AnnAssign) -> list[str]:
    targets: list[str] = []
    if isinstance(node, ast.Assign):
        raw_targets = node.targets
    else:
        raw_targets = [node.target]
    for target in raw_targets:
        if isinstance(target, ast.Name):
            targets.append(target.id)
    return targets


def _is_alias_value(node: ast.AST | None) -> bool:
    return isinstance(node, (ast.Name, ast.Attribute))


def _add_public_symbol(
    records: dict[str, dict[str, object]],
    *,
    name: str,
    kind: str,
    in_all: bool,
    is_alias: bool,
) -> None:
    if name.startswith("_"):
        return
    existing = records.get(name)
    if existing is None:
        records[name] = {
            "name": name,
            "kind": kind,
            "in___all__": in_all,
            "is_alias": is_alias,
        }
        return
    existing["in___all__"] = bool(existing["in___all__"]) or in_all
    existing["is_alias"] = bool(existing["is_alias"]) or is_alias
    if existing["kind"] in {"import", "variable", "unknown"} and kind not in {"import", "variable", "unknown"}:
        existing["kind"] = kind


def _public_symbols_from_tree(tree: ast.Module, exported_names: set[str]) -> list[dict[str, object]]:
    records: dict[str, dict[str, object]] = {}

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            _add_public_symbol(
                records,
                name=node.name,
                kind="class",
                in_all=node.name in exported_names,
                is_alias=False,
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _add_public_symbol(
                records,
                name=node.name,
                kind="function",
                in_all=node.name in exported_names,
                is_alias=False,
            )
        elif isinstance(node, ast.Assign):
            for name in _assignment_target_names(node):
                _add_public_symbol(
                    records,
                    name=name,
                    kind="alias" if _is_alias_value(node.value) else ("constant" if name.isupper() else "variable"),
                    in_all=name in exported_names,
                    is_alias=_is_alias_value(node.value),
                )
        elif isinstance(node, ast.AnnAssign):
            for name in _assignment_target_names(node):
                _add_public_symbol(
                    records,
                    name=name,
                    kind="alias" if _is_alias_value(node.value) else ("constant" if name.isupper() else "variable"),
                    in_all=name in exported_names,
                    is_alias=_is_alias_value(node.value),
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                public_name = alias.asname or alias.name.split(".")[-1]
                if exported_names and public_name not in exported_names:
                    continue
                _add_public_symbol(
                    records,
                    name=public_name,
                    kind="import",
                    in_all=public_name in exported_names,
                    is_alias=True,
                )
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue
                public_name = alias.asname or alias.name
                if exported_names and public_name not in exported_names:
                    continue
                _add_public_symbol(
                    records,
                    name=public_name,
                    kind="import",
                    in_all=public_name in exported_names,
                    is_alias=True,
                )

    names_to_keep = exported_names or {name for name in records if not name.startswith("_")}
    for name in names_to_keep:
        if name not in records:
            records[name] = {
                "name": name,
                "kind": "unknown",
                "in___all__": name in exported_names,
                "is_alias": False,
            }

    return [records[name] for name in sorted(names_to_keep)]


def _legacy_public_contract_paths(root: Path) -> list[str]:
    path = root / "tests" / "contracts" / "api" / "test_legacy_public_modules_absent.py"
    if not path.exists():
        return []
    tree = _parse_tree(path, root=root)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "parametrize":
            if len(node.args) < 2:
                continue
            if not isinstance(node.args[0], ast.Constant) or node.args[0].value != "module_name":
                continue
            values = _static_string_sequence(node.args[1])
            if values is not None:
                return values
    return []


def _module_is_importable(root: Path, module_name: str) -> bool:
    _ensure_src_on_path(root)
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


def _canonical_public_package_inventory(root: Path, module_name: str) -> dict[str, object]:
    init_path = root / "src" / Path(module_name.replace(".", "/")) / "__init__.py"
    tree = _parse_tree(init_path, root=root)
    facade_info = _top_level_tree_info(tree)
    exports = _runtime_all(root, module_name)
    return {
        "file": _relative_path_text(root, init_path),
        "all": exports,
        "facade": {
            "uses_import_module": bool(facade_info["uses_import_module"]),
            "uses___getattr__": bool(facade_info["uses___getattr__"]),
            "uses___dir__": bool(facade_info["uses___dir__"]),
            "routing_tables": list(facade_info["routing_tables"]),
        },
        "exports": [_runtime_export_record(root, module_name, export_name) for export_name in exports],
    }


def _drain_bucket_inventory(root: Path, bucket_name: str) -> dict[str, object]:
    bucket_path = root / "src" / "fuggers_py" / bucket_name
    modules: list[dict[str, object]] = []
    if not bucket_path.exists():
        return {"modules": modules}

    for path in sorted(bucket_path.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = _parse_tree(path, root=root)
        module_name = _module_name_for_path(root, path)
        facade_info = _top_level_tree_info(tree)
        static_all = facade_info["static_all"]
        if isinstance(static_all, list):
            exported_names = static_all
        elif bool(facade_info["uses___getattr__"]) or bool(facade_info["uses_import_module"]):
            try:
                exported_names = _runtime_all(root, module_name)
            except Exception:
                exported_names = []
        else:
            exported_names = []
        modules.append(
            {
                "module": module_name,
                "file": _relative_path_text(root, path),
                "exported_names": exported_names,
                "facade": {
                    "uses_import_module": bool(facade_info["uses_import_module"]),
                    "uses___getattr__": bool(facade_info["uses___getattr__"]),
                    "uses___dir__": bool(facade_info["uses___dir__"]),
                    "routing_tables": list(facade_info["routing_tables"]),
                },
                "public_symbols": _public_symbols_from_tree(tree, set(exported_names)),
            }
        )
    return {"modules": modules}


def build_public_api_current_inventory(root: Path) -> dict[str, object]:
    _purge_loaded_package_modules("fuggers_py")
    canonical_public_packages = {
        module_name: _canonical_public_package_inventory(root, module_name)
        for module_name in CANONICAL_PUBLIC_PACKAGES
    }
    retired_contract_paths = _legacy_public_contract_paths(root)
    currently_importable = [
        module_name
        for module_name in retired_contract_paths
        if _module_is_importable(root, module_name)
    ]
    drain_list_inventory = {
        bucket_name: _drain_bucket_inventory(root, bucket_name)
        for bucket_name in DRAIN_BUCKETS
    }
    return {
        "schema_version": 1,
        "canonical_public_packages": canonical_public_packages,
        "legacy_public_import_paths": {
            "currently_importable": currently_importable,
            "retired_contract_paths": retired_contract_paths,
        },
        "drain_list_inventory": drain_list_inventory,
    }


def freeze_public_api_current_inventory(root: Path, *, output_path: Path) -> Path:
    payload = build_public_api_current_inventory(root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return output_path


def _load_current_inventory(root: Path) -> dict[str, object]:
    inventory_error = _current_inventory_error(root)
    if inventory_error is not None:
        raise ValueError(inventory_error)
    return _json_load(root / CURRENT_INVENTORY_RELATIVE_PATH)


def _canonical_public_exports_by_package(
    inventory: dict[str, object],
) -> dict[str, list[dict[str, object]]]:
    packages = inventory["canonical_public_packages"]
    assert isinstance(packages, dict)
    return {str(package_name): list(package_data["exports"]) for package_name, package_data in packages.items()}


def _symbol_to_non_root_public_packages(
    inventory: dict[str, object],
) -> dict[str, list[str]]:
    mapping: dict[str, set[str]] = {}
    for package_name, exports in _canonical_public_exports_by_package(inventory).items():
        if package_name == "fuggers_py":
            continue
        for export_row in exports:
            mapping.setdefault(str(export_row["name"]), set()).add(package_name)
    return {symbol_name: sorted(package_names) for symbol_name, package_names in mapping.items()}


def _public_resolved_keys(inventory: dict[str, object]) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for exports in _canonical_public_exports_by_package(inventory).values():
        for export_row in exports:
            resolved_module = export_row.get("resolved_module")
            if isinstance(resolved_module, str):
                keys.add((resolved_module, str(export_row["name"])))
    return keys


def _canonical_owner_for_public_export(public_package: str, export_row: dict[str, object]) -> str:
    export_name = str(export_row["name"])
    if public_package == "fuggers_py":
        if export_name in TARGET_PUBLIC_MODULES:
            return f"fuggers_py.{export_name}"
        return ROOT_SHARED_OWNER_OVERRIDES.get(export_name, "fuggers_py")
    return public_package


def build_public_api_export_manifest(root: Path) -> dict[str, object]:
    inventory = _load_current_inventory(root)
    packages: dict[str, dict[str, object]] = {}
    exports_by_package = _canonical_public_exports_by_package(inventory)
    for package_name in CANONICAL_PUBLIC_PACKAGES:
        exports = sorted(exports_by_package[package_name], key=lambda row: str(row["name"]))
        packages[package_name] = {
            "exports": [
                {
                    "name": str(export_row["name"]),
                    "kind": str(export_row["kind"]),
                    "owning_package": _canonical_owner_for_public_export(package_name, export_row),
                }
                for export_row in exports
            ]
        }
    return {
        "schema_version": 1,
        "packages": packages,
    }


def _replacement_import_path(legacy_import_path: str) -> str | None:
    best_match: tuple[int, str] | None = None
    for old_path, new_path in LEGACY_IMPORT_REPLACEMENTS.items():
        if legacy_import_path == old_path or legacy_import_path.startswith(old_path + "."):
            score = len(old_path)
            if best_match is None or score > best_match[0]:
                best_match = (score, new_path)
    if best_match is None:
        return None
    return best_match[1]


def build_public_api_legacy_denylist(root: Path) -> dict[str, object]:
    inventory = _load_current_inventory(root)
    legacy_paths = inventory["legacy_public_import_paths"]["retired_contract_paths"]
    return {
        "schema_version": 1,
        "entries": [
            {
                "legacy_import_path": legacy_import_path,
                "replacement_import_path": _replacement_import_path(str(legacy_import_path)),
                "reason": "legacy_public_module",
                "must_fail": True,
            }
            for legacy_import_path in sorted(str(path) for path in legacy_paths)
        ],
    }


def _canonical_owner_for_drain_symbol(
    module_name: str,
    *,
    symbol_name: str,
    symbol_to_public_packages: dict[str, list[str]],
) -> str:
    if symbol_name in ROOT_SHARED_OWNER_OVERRIDES:
        return ROOT_SHARED_OWNER_OVERRIDES[symbol_name]
    if module_name.startswith("fuggers_py._curves_impl"):
        return "fuggers_py.curves"
    if module_name.startswith("fuggers_py._vol_surfaces_impl"):
        return "fuggers_py.vol_surfaces"
    if module_name.startswith("fuggers_py._products.bonds") or module_name.startswith("fuggers_py._pricers.bonds"):
        return "fuggers_py.bonds"
    if module_name.startswith("fuggers_py._products.credit") or module_name.startswith("fuggers_py._pricers.credit"):
        return "fuggers_py.credit"
    if module_name.startswith("fuggers_py._measures.credit"):
        return "fuggers_py.credit"
    if module_name.startswith("fuggers_py._products.funding") or module_name.startswith("fuggers_py._measures.funding"):
        return "fuggers_py.funding"
    if module_name.startswith("fuggers_py._reference.inflation") or module_name.startswith("fuggers_py._measures.inflation"):
        return "fuggers_py.inflation"
    if module_name.startswith("fuggers_py._products.rates") or module_name.startswith("fuggers_py._pricers.rates"):
        if "inflation" in module_name:
            return "fuggers_py.inflation"
        return "fuggers_py.rates"
    if module_name == "fuggers_py._market.indices.bond_index":
        return "fuggers_py.bonds"
    if module_name in {
        "fuggers_py._market.indices.conventions",
        "fuggers_py._market.indices.fixing_store",
        "fuggers_py._market.indices.overnight",
    }:
        return "fuggers_py.rates"
    if module_name == "fuggers_py._market.curve_support":
        return "fuggers_py.curves"
    if module_name == "fuggers_py._market._shared" or module_name.startswith("fuggers_py._reference.base"):
        return "fuggers_py._core"
    if module_name in {"fuggers_py._market.snapshot", "fuggers_py._market.sources", "fuggers_py._market.state"}:
        return "fuggers_py._runtime"
    if module_name.startswith("fuggers_py._calc"):
        return "fuggers_py._runtime"
    if module_name.startswith("fuggers_py._adapters"):
        return "fuggers_py._storage"
    if module_name.startswith("fuggers_py._reference.bonds") or module_name.startswith("fuggers_py._reference.reference_data"):
        return "fuggers_py.bonds"
    if module_name.startswith("fuggers_py._reference"):
        return "fuggers_py._core"
    if module_name.startswith("fuggers_py._measures.yields"):
        return "fuggers_py.bonds"
    if module_name.startswith("fuggers_py._measures.yas"):
        return "fuggers_py.bonds"
    if module_name.startswith("fuggers_py._measures.cashflows"):
        return "fuggers_py.bonds"
    if module_name.startswith("fuggers_py._measures.spreads"):
        return "fuggers_py.bonds"
    if module_name.startswith("fuggers_py._measures.rv"):
        return "fuggers_py.bonds"
    if module_name.startswith("fuggers_py._measures.risk.hedging.portfolio") or module_name.startswith("fuggers_py._measures.risk.var"):
        return "fuggers_py.portfolio"
    if module_name.startswith("fuggers_py._measures.risk"):
        return "fuggers_py.bonds"
    if module_name.startswith("fuggers_py._measures.options"):
        public_packages = symbol_to_public_packages.get(symbol_name, [])
        if public_packages:
            return public_packages[0]
        return "fuggers_py.rates"
    if module_name.startswith("fuggers_py._measures"):
        return "fuggers_py.bonds"
    if module_name.startswith("fuggers_py._products.instruments"):
        return "fuggers_py._core"
    public_packages = symbol_to_public_packages.get(symbol_name, [])
    if public_packages:
        return public_packages[0]
    return "fuggers_py._core"


def _decision_for_drain_symbol(
    module_row: dict[str, object],
    symbol_row: dict[str, object],
    *,
    public_resolved_keys: set[tuple[str, str]],
    symbol_to_public_packages: dict[str, list[str]],
) -> str:
    module_name = str(module_row["module"])
    symbol_name = str(symbol_row["name"])
    if str(symbol_row["kind"]) == "import":
        return "delete"
    if (
        str(module_row["file"]).endswith("__init__.py")
        and str(symbol_row["kind"]) == "unknown"
        and (module_name, symbol_name) not in public_resolved_keys
    ):
        return "delete"
    owner = _canonical_owner_for_drain_symbol(
        module_name,
        symbol_name=symbol_name,
        symbol_to_public_packages=symbol_to_public_packages,
    )
    if (module_name, symbol_name) in public_resolved_keys:
        return f"move to {owner}"
    return f"internalize under {owner}"


def build_public_api_migration_ledger(root: Path) -> dict[str, object]:
    inventory = _load_current_inventory(root)
    symbol_to_public_packages = _symbol_to_non_root_public_packages(inventory)
    public_resolved_keys = _public_resolved_keys(inventory)
    entries: list[dict[str, object]] = []

    for public_package in CANONICAL_PUBLIC_PACKAGES:
        exports = sorted(
            _canonical_public_exports_by_package(inventory)[public_package],
            key=lambda row: str(row["name"]),
        )
        for export_row in exports:
            owner = _canonical_owner_for_public_export(public_package, export_row)
            entries.append(
                {
                    "entry_id": f"public:{public_package}:{export_row['name']}",
                    "source_kind": "canonical_public_export",
                    "public_package": public_package,
                    "symbol": str(export_row["name"]),
                    "symbol_kind": str(export_row["kind"]),
                    "current_module": export_row.get("resolved_module"),
                    "current_file": export_row.get("resolved_file"),
                    "decision": f"move to {owner}",
                }
            )

    drain_inventory = inventory["drain_list_inventory"]
    assert isinstance(drain_inventory, dict)
    for bucket_name in DRAIN_BUCKETS:
        bucket_data = drain_inventory[bucket_name]
        for module_row in sorted(bucket_data["modules"], key=lambda row: str(row["module"])):
            module_name = str(module_row["module"])
            for symbol_row in sorted(module_row["public_symbols"], key=lambda row: str(row["name"])):
                entries.append(
                    {
                        "entry_id": f"drain:{module_name}:{symbol_row['name']}",
                        "source_kind": "drain_list_symbol",
                        "bucket": bucket_name,
                        "module": module_name,
                        "file": module_row["file"],
                        "symbol": str(symbol_row["name"]),
                        "symbol_kind": str(symbol_row["kind"]),
                        "in___all__": bool(symbol_row["in___all__"]),
                        "is_alias": bool(symbol_row["is_alias"]),
                        "decision": _decision_for_drain_symbol(
                            module_row,
                            symbol_row,
                            public_resolved_keys=public_resolved_keys,
                            symbol_to_public_packages=symbol_to_public_packages,
                        ),
                    }
                )

    return {
        "schema_version": 1,
        "entries": entries,
    }


def freeze_public_api_export_controls(root: Path) -> list[Path]:
    outputs = [
        (root / EXPORT_MANIFEST_RELATIVE_PATH, build_public_api_export_manifest(root)),
        (root / LEGACY_DENYLIST_RELATIVE_PATH, build_public_api_legacy_denylist(root)),
        (root / MIGRATION_LEDGER_RELATIVE_PATH, build_public_api_migration_ledger(root)),
    ]
    written: list[Path] = []
    for output_path, payload in outputs:
        _json_dump(output_path, payload)
        written.append(output_path)
    return written


def _load_export_manifest(root: Path) -> dict[str, object]:
    return _json_load(root / EXPORT_MANIFEST_RELATIVE_PATH)


def _public_package_dir(root: Path, package_name: str) -> Path:
    if package_name == "fuggers_py":
        return root / "src" / "fuggers_py"
    return root / "src" / "fuggers_py" / package_name.split(".")[-1]


def _canonical_public_tree_entries(root: Path, package_name: str) -> list[str]:
    package_dir = _public_package_dir(root, package_name)
    if package_name == "fuggers_py":
        return ["__init__.py"]
    entries: list[str] = []
    for path in sorted(package_dir.rglob("*")):
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(package_dir).as_posix()
        if path.is_dir():
            entries.append(relative + "/")
        elif path.is_file():
            entries.append(relative)
    return entries


def build_public_api_structure_manifest(root: Path) -> dict[str, object]:
    top_level_packages: dict[str, dict[str, str]] = {}
    src_root = root / "src" / "fuggers_py"
    for path in sorted(p for p in src_root.iterdir() if p.is_dir() and p.name != "__pycache__"):
        if path.name in TARGET_PUBLIC_MODULES:
            role = "canonical_public"
            planned_action = "keep"
        elif path.name in INTERNAL_SURVIVOR_TOP_LEVEL_PACKAGES:
            role = "internal_survivor"
            planned_action = "keep"
        else:
            role = "transition_bucket"
            planned_action = "delete"
        top_level_packages[path.name] = {
            "role": role,
            "planned_action": planned_action,
        }

    canonical_public_package_trees = {
        package_name.split(".")[-1]: _canonical_public_tree_entries(root, package_name)
        for package_name in CANONICAL_PUBLIC_PACKAGES
        if package_name != "fuggers_py"
    }

    return {
        "schema_version": 1,
        "phase": "phase1_slice3",
        "root_package": "fuggers_py",
        "top_level_packages": top_level_packages,
        "canonical_public_package_trees": canonical_public_package_trees,
    }


def _allowed_dependency_targets() -> set[str]:
    return {
        "fuggers_py._core",
        "fuggers_py._math",
        "fuggers_py._runtime",
        "fuggers_py._storage",
        *CANONICAL_PUBLIC_PACKAGES,
    }


def _drain_bucket_module_prefixes() -> tuple[str, ...]:
    return tuple(f"fuggers_py.{bucket_name}" for bucket_name in DRAIN_BUCKETS)


def _is_drain_bucket_module(module_name: str) -> bool:
    return any(
        module_name == prefix or module_name.startswith(prefix + ".")
        for prefix in _drain_bucket_module_prefixes()
    )


def _module_belongs_to_owner(module_name: str, owner_package: str) -> bool:
    return module_name == owner_package or module_name.startswith(owner_package + ".")


def _file_belongs_to_owner(path_text: str, owner_package: str) -> bool:
    relative_prefix = "src/" + owner_package.replace(".", "/")
    return path_text == f"{relative_prefix}.py" or path_text.startswith(relative_prefix + "/")


def _module_name_from_path(root: Path, path: Path) -> str:
    relative = path.relative_to(root / "src" / "fuggers_py").with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return "fuggers_py" + ("." + ".".join(parts) if parts else "")


def _dependency_source_files(root: Path, package_name: str) -> list[Path]:
    package_dir = _public_package_dir(root, package_name)
    if package_name == "fuggers_py":
        return [package_dir / "__init__.py"]
    return sorted(path for path in package_dir.rglob("*.py") if "__pycache__" not in path.parts)


def _current_package_for_path(root: Path, path: Path) -> str:
    package_root = root / "src" / "fuggers_py"
    if not path.is_relative_to(package_root):
        return ""
    current_module = _module_name_from_path(root, path)
    return current_module if path.name == "__init__.py" else current_module.rsplit(".", 1)[0]


def _resolved_import_base_module(current_package: str, node: ast.ImportFrom) -> str:
    if node.level == 0:
        if node.module is None:
            return ""
        base_module = node.module
    else:
        base_parts = current_package.split(".")
        trim_count = max(node.level - 1, 0)
        if trim_count:
            base_parts = base_parts[:-trim_count]
        if node.module is None:
            base_module = ".".join(base_parts)
        else:
            base_module = ".".join([*base_parts, node.module])
    return base_module


def _resolved_import_from_modules(current_package: str, node: ast.ImportFrom) -> set[str]:
    base_module = _resolved_import_base_module(current_package, node)
    imported_modules: set[str] = set()
    if base_module:
        imported_modules.add(base_module)
    for alias in node.names:
        if alias.name == "*" or not base_module:
            continue
        imported_modules.add(f"{base_module}.{alias.name}")
    return imported_modules


def _resolved_import_modules_for_path(root: Path, path: Path) -> set[str]:
    tree = _parse_tree(path, root=root)
    current_package = _current_package_for_path(root, path)
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported_modules.update(_resolved_import_from_modules(current_package, node))
    return imported_modules


def _moved_phase1_symbol_import_errors(root: Path, delta_paths: set[str]) -> list[str]:
    errors: list[str] = []
    for relative_path in sorted(delta_paths):
        if not relative_path.endswith(".py"):
            continue
        if not (relative_path.startswith("src/") or relative_path.startswith("tests/")):
            continue
        path = root / relative_path
        if not path.exists():
            continue
        tree = _parse_tree(path, root=root)
        current_package = _current_package_for_path(root, path)
        seen: set[tuple[str, int, str, str]] = set()
        old_import_aliases: dict[str, str] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name
                    if any(
                        module_name == prefix or module_name.startswith(prefix + ".")
                        for prefix in PHASE1_OLD_BUCKET_IMPORT_PREFIXES
                    ):
                        old_import_aliases[alias.asname or module_name.split(".")[-1]] = module_name
            elif isinstance(node, ast.ImportFrom):
                base_module = _resolved_import_base_module(current_package, node)
                if not base_module or not any(
                    base_module == prefix or base_module.startswith(prefix + ".")
                    for prefix in PHASE1_OLD_BUCKET_IMPORT_PREFIXES
                ):
                    continue
                for alias in node.names:
                    if alias.name not in PHASE1_MOVED_SYMBOLS:
                        continue
                    seen.add((relative_path, node.lineno, alias.name, base_module))

        class _OldImportAttributeVisitor(ast.NodeVisitor):
            def visit_Attribute(self, node: ast.Attribute) -> None:
                if isinstance(node.value, ast.Name):
                    module_name = old_import_aliases.get(node.value.id)
                    if module_name is not None and node.attr in PHASE1_MOVED_SYMBOLS:
                        seen.add((relative_path, node.lineno, node.attr, module_name))
                self.generic_visit(node)

        _OldImportAttributeVisitor().visit(tree)

        for path_text, lineno, symbol_name, module_name in sorted(seen):
            target_module = PHASE1_MOVED_SYMBOL_FINAL_IMPORT_MODULES[symbol_name]
            errors.append(
                f"{path_text}:{lineno} imports moved Phase 1 name `{symbol_name}` from old bucket module "
                f"`{module_name}`. Import it from `{target_module}` instead."
            )
    return errors


def _core_self_contained_import_errors(root: Path, delta_paths: set[str]) -> list[str]:
    errors: list[str] = []
    for relative_path in sorted(delta_paths):
        if relative_path not in CORE_SELF_CONTAINED_OWNER_RELATIVE_PATHS:
            continue
        path = root / relative_path
        if not path.exists():
            continue
        tree = _parse_tree(path, root=root)
        current_package = _current_package_for_path(root, path)
        offending_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                offending_modules.update(
                    alias.name
                    for alias in node.names
                    if alias.name == CORE_SELF_CONTAINED_FORBIDDEN_IMPORT_PREFIX
                    or alias.name.startswith(CORE_SELF_CONTAINED_FORBIDDEN_IMPORT_PREFIX + ".")
                )
            elif isinstance(node, ast.ImportFrom):
                base_module = _resolved_import_base_module(current_package, node)
                if base_module == CORE_SELF_CONTAINED_FORBIDDEN_IMPORT_PREFIX or base_module.startswith(
                    CORE_SELF_CONTAINED_FORBIDDEN_IMPORT_PREFIX + "."
                ):
                    offending_modules.add(base_module)
        for module_name in sorted(offending_modules):
            errors.append(
                f"{relative_path} imports old bond support module `{module_name}`. "
                "`fuggers_py._core` owners must import shared support from local `_core` modules instead."
            )
    return errors


def _canonical_public_python_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    root_init = root / "src" / "fuggers_py" / "__init__.py"
    if root_init.exists():
        paths.append(root_init)
    for module_name in TARGET_PUBLIC_MODULES:
        package_dir = root / "src" / "fuggers_py" / module_name
        if not package_dir.exists():
            continue
        paths.extend(sorted(path for path in package_dir.rglob("*.py") if "__pycache__" not in path.parts))
    return paths


def _canonical_public_entrypoint_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in [root / "src" / "fuggers_py" / "__init__.py", *(
        root / "src" / "fuggers_py" / module_name / "__init__.py" for module_name in TARGET_PUBLIC_MODULES
    )]:
        if path.exists():
            paths.append(path)
    return paths


def _canonical_public_direct_import_surface_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in (
        root / "src" / "fuggers_py" / "__init__.py",
        root / "src" / "fuggers_py" / "bonds" / "__init__.py",
        root / "src" / "fuggers_py" / "rates" / "__init__.py",
        root / "src" / "fuggers_py" / "inflation" / "__init__.py",
        root / "src" / "fuggers_py" / "credit" / "__init__.py",
        root / "src" / "fuggers_py" / "funding" / "__init__.py",
        root / "src" / "fuggers_py" / "curves" / "__init__.py",
        root / "src" / "fuggers_py" / "vol_surfaces" / "__init__.py",
    ):
        if path.exists():
            paths.append(path)
    return paths


def _dynamic_routing_primitives_for_path(root: Path, path: Path) -> list[str]:
    tree = _parse_tree(path, root=root)
    primitives: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "__getattr__":
            primitives.add("__getattr__")
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func_name = _dotted_name(child.func)
                if func_name in {"import_module", "importlib.import_module", "__import__"}:
                    primitives.add(func_name)
            if isinstance(child, ast.Attribute) and _dotted_name(child) == "sys.modules":
                primitives.add("sys.modules")
    return sorted(primitives)


def _canonical_public_dynamic_import_inventory(root: Path) -> dict[str, list[str]]:
    inventory: dict[str, list[str]] = {}
    for path in _canonical_public_direct_import_surface_paths(root):
        primitives = _dynamic_routing_primitives_for_path(root, path)
        if primitives:
            inventory[str(path.relative_to(root))] = primitives
    return inventory


def _canonical_public_dynamic_import_errors(root: Path, delta_paths: set[str]) -> list[str]:
    errors: list[str] = []
    del delta_paths
    for path in _canonical_public_direct_import_surface_paths(root):
        relative_path = path.relative_to(root)
        primitives = _dynamic_routing_primitives_for_path(root, path)
        if not primitives:
            continue
        primitive = primitives[0]
        errors.append(
            f"{relative_path} uses `{primitive}` in a canonical public package. "
            "Canonical public packages must use direct imports only."
        )
    return errors


def _canonical_public_module_reassignment_errors(root: Path, delta_paths: set[str]) -> list[str]:
    errors: list[str] = []
    del delta_paths
    for path in _canonical_public_python_paths(root):
        tree = _parse_tree(path, root=root)
        relative_path = path.relative_to(root)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, ast.AnnAssign):
                targets = [node.target]
            else:
                targets = []
            if any(isinstance(target, ast.Attribute) and target.attr == "__module__" for target in targets):
                errors.append(
                    f"{relative_path} reassigns `__module__` in a canonical public package. "
                    "Move the code to the real owner instead of rewriting ownership metadata."
                )
                break
            if isinstance(node, ast.Call):
                func_name = _dotted_name(node.func)
                if func_name != "setattr" or len(node.args) < 2:
                    continue
                module_arg = node.args[1]
                if isinstance(module_arg, ast.Constant) and module_arg.value == "__module__":
                    errors.append(
                        f"{relative_path} reassigns `__module__` in a canonical public package. "
                        "Move the code to the real owner instead of rewriting ownership metadata."
                    )
                    break
    return errors


def _canonical_public_drain_bucket_import_errors(root: Path, delta_paths: set[str]) -> list[str]:
    errors: list[str] = []
    del delta_paths
    for path in _canonical_public_python_paths(root):
        relative_path = str(path.relative_to(root))
        forbidden_modules = sorted(
            {
                imported_module
                for imported_module in _resolved_import_modules_for_path(root, path)
                if _is_drain_bucket_module(imported_module)
            }
        )
        if not forbidden_modules:
            continue
        errors.append(
            f"{relative_path} imports forbidden drain bucket module `{forbidden_modules[0]}`. "
            "Canonical public packages must own live code under the public tree instead of importing drain-list buckets."
        )
    return errors


def _manifest_owner_by_export(root: Path) -> dict[tuple[str, str], str]:
    manifest = _load_export_manifest(root)
    packages = manifest.get("packages", {})
    if not isinstance(packages, dict):
        return {}

    owner_by_export: dict[tuple[str, str], str] = {}
    for package_name, package_data in packages.items():
        if not isinstance(package_name, str) or not isinstance(package_data, dict):
            continue
        exports = package_data.get("exports", [])
        if not isinstance(exports, list):
            continue
        for export_row in exports:
            if not isinstance(export_row, dict):
                continue
            export_name = export_row.get("name")
            owner_package = export_row.get("owning_package")
            if isinstance(export_name, str) and isinstance(owner_package, str):
                owner_by_export[(package_name, export_name)] = owner_package
    return owner_by_export


def _canonical_public_source_ownership_errors(root: Path, delta_paths: set[str]) -> list[str]:
    errors: list[str] = []
    del delta_paths
    owner_by_export = _manifest_owner_by_export(root)
    _purge_loaded_package_modules("fuggers_py")

    for package_name in CANONICAL_PUBLIC_PACKAGES:
        try:
            inventory = _canonical_public_package_inventory(root, package_name)
        except Exception as exc:
            continue

        exports = inventory.get("exports", [])
        if not isinstance(exports, list):
            continue

        for export_row in exports:
            if not isinstance(export_row, dict):
                continue
            export_name = export_row.get("name")
            if not isinstance(export_name, str):
                continue
            owner_package = owner_by_export.get((package_name, export_name))
            if owner_package is None:
                continue

            resolved_module = export_row.get("resolved_module")
            resolved_file = export_row.get("resolved_file")
            module_matches = isinstance(resolved_module, str) and _module_belongs_to_owner(resolved_module, owner_package)
            file_matches = isinstance(resolved_file, str) and _file_belongs_to_owner(resolved_file, owner_package)
            if module_matches or file_matches:
                continue

            if isinstance(resolved_module, str):
                location_text = f"`{resolved_module}`"
            elif isinstance(resolved_file, str):
                location_text = f"`{resolved_file}`"
            else:
                location_text = "an unknown runtime location"

            errors.append(
                f"{package_name} export `{export_name}` declares owner `{owner_package}` but still resolves to "
                f"{location_text}. Move the live implementation under `{owner_package}`."
            )
    return errors


def _collapse_dependency_target(module_name: str) -> str | None:
    for target_name in sorted(_allowed_dependency_targets(), key=len, reverse=True):
        if module_name == target_name or module_name.startswith(target_name + "."):
            return target_name
    return None


def _current_allowed_dependency_edges(root: Path) -> dict[str, set[str]]:
    edges = {package_name: set() for package_name in CANONICAL_PUBLIC_PACKAGES}
    for package_name in CANONICAL_PUBLIC_PACKAGES:
        for path in _dependency_source_files(root, package_name):
            for imported_module in _resolved_import_modules_for_path(root, path):
                target_name = _collapse_dependency_target(imported_module)
                if target_name is None:
                    continue
                if target_name == package_name:
                    continue
                if package_name != "fuggers_py" and target_name == "fuggers_py":
                    continue
                edges[package_name].add(target_name)
    return edges


def build_public_api_dependency_manifest(root: Path) -> dict[str, object]:
    export_manifest = _load_export_manifest(root)
    current_edges = _current_allowed_dependency_edges(root)
    packages: dict[str, dict[str, list[str]]] = {}
    root_owner_targets = {
        str(export_row["owning_package"])
        for export_row in export_manifest["packages"]["fuggers_py"]["exports"]
        if isinstance(export_row.get("owning_package"), str)
    }

    for package_name in CANONICAL_PUBLIC_PACKAGES:
        allowed_targets = set(TARGET_DEPENDENCY_BASELINE.get(package_name, set()))
        allowed_targets.update(current_edges.get(package_name, set()))
        if package_name == "fuggers_py":
            allowed_targets.update(root_owner_targets)
        allowed_targets.discard(package_name)
        allowed_targets = {target for target in allowed_targets if target in _allowed_dependency_targets()}
        if package_name != "fuggers_py":
            allowed_targets.discard("fuggers_py")
        packages[package_name] = {
            "allowed_targets": sorted(allowed_targets),
        }

    return {
        "schema_version": 1,
        "packages": packages,
    }


def freeze_public_api_structure_controls(root: Path) -> list[Path]:
    outputs = [
        (root / STRUCTURE_MANIFEST_RELATIVE_PATH, build_public_api_structure_manifest(root)),
        (root / DEPENDENCY_MANIFEST_RELATIVE_PATH, build_public_api_dependency_manifest(root)),
    ]
    written: list[Path] = []
    for output_path, payload in outputs:
        _json_dump(output_path, payload)
        written.append(output_path)
    return written


def _current_inventory_error(root: Path) -> str | None:
    inventory_path = root / CURRENT_INVENTORY_RELATIVE_PATH
    if not inventory_path.exists():
        return (
            f"Missing `{CURRENT_INVENTORY_RELATIVE_PATH}`. "
            "Phase 1 slice 1 must freeze the current public and drain-list inventory before later slices."
        )
    try:
        payload = _json_load(inventory_path)
    except json.JSONDecodeError as exc:
        return f"`{CURRENT_INVENTORY_RELATIVE_PATH}` is not valid JSON: {exc.msg}."
    required_keys = {"schema_version", "canonical_public_packages", "legacy_public_import_paths", "drain_list_inventory"}
    missing = sorted(required_keys - set(payload))
    if missing:
        joined = ", ".join(missing)
        return f"`{CURRENT_INVENTORY_RELATIVE_PATH}` is missing required keys: {joined}."
    return None


def _slice2_control_files_error(root: Path) -> str | None:
    control_files = {
        EXPORT_MANIFEST_RELATIVE_PATH: {"schema_version", "packages"},
        LEGACY_DENYLIST_RELATIVE_PATH: {"schema_version", "entries"},
        MIGRATION_LEDGER_RELATIVE_PATH: {"schema_version", "entries"},
    }
    for relative_path, required_keys in control_files.items():
        path = root / relative_path
        if not path.exists():
            return (
                f"Missing `{relative_path}`. "
                "Phase 1 slice 2 must freeze the export manifest, legacy denylist, and migration ledger before later slices."
            )
        try:
            payload = _json_load(path)
        except json.JSONDecodeError as exc:
            return f"`{relative_path}` is not valid JSON: {exc.msg}."
        missing = sorted(required_keys - set(payload))
        if missing:
            return f"`{relative_path}` is missing required keys: {', '.join(missing)}."
    return None


def _slice3_control_files_error(root: Path) -> str | None:
    control_files = {
        STRUCTURE_MANIFEST_RELATIVE_PATH: {"schema_version", "phase", "root_package", "top_level_packages", "canonical_public_package_trees"},
        DEPENDENCY_MANIFEST_RELATIVE_PATH: {"schema_version", "packages"},
    }
    for relative_path, required_keys in control_files.items():
        path = root / relative_path
        if not path.exists():
            return (
                f"Missing `{relative_path}`. "
                "Phase 1 slice 3 must freeze the structure manifest and dependency manifest before later slices."
            )
        try:
            payload = _json_load(path)
        except json.JSONDecodeError as exc:
            return f"`{relative_path}` is not valid JSON: {exc.msg}."
        missing = sorted(required_keys - set(payload))
        if missing:
            return f"`{relative_path}` is missing required keys: {', '.join(missing)}."
    return None


def _is_planning_support_path(path_text: str) -> bool:
    return path_text in PLANNING_SUPPORT_PATHS or path_text.startswith("refactor/")


def _planning_change_set_errors(delta_paths: set[str]) -> list[str]:
    changed_frozen_artifacts = sorted(FROZEN_PLANNING_ARTIFACT_PATHS & delta_paths)
    if not changed_frozen_artifacts:
        return []

    non_planning_paths = sorted(path_text for path_text in delta_paths if not _is_planning_support_path(path_text))
    if not non_planning_paths:
        return []

    frozen_joined = ", ".join(changed_frozen_artifacts)
    non_planning_joined = ", ".join(non_planning_paths[:3])
    if len(non_planning_paths) > 3:
        non_planning_joined += ", ..."
    return [
        "Frozen planning artifacts changed together with non-planning files. "
        f"Planning artifacts: {frozen_joined}. Non-planning files: {non_planning_joined}. "
        "Update target docs or control manifests only in a separate planning change set."
    ]


def _slice3_manifest_exactness_error(root: Path) -> str | None:
    structure_manifest = _json_load(root / STRUCTURE_MANIFEST_RELATIVE_PATH)
    expected_structure_manifest = build_public_api_structure_manifest(root)
    if structure_manifest != expected_structure_manifest:
        return (
            f"`{STRUCTURE_MANIFEST_RELATIVE_PATH}` no longer matches the exact `src/fuggers_py` tree. "
            "The full structure manifest must pass on every sealed change set."
        )

    dependency_manifest = _json_load(root / DEPENDENCY_MANIFEST_RELATIVE_PATH)
    expected_dependency_manifest = build_public_api_dependency_manifest(root)
    if dependency_manifest != expected_dependency_manifest:
        return (
            f"`{DEPENDENCY_MANIFEST_RELATIVE_PATH}` no longer matches the exact allowed import-edge set. "
            "The full dependency manifest must pass on every sealed change set."
        )

    return None


def _path_is_user_facing(path_text: str) -> bool:
    if path_text in {
        CURRENT_INVENTORY_RELATIVE_PATH,
        EXPORT_MANIFEST_RELATIVE_PATH,
        LEGACY_DENYLIST_RELATIVE_PATH,
        MIGRATION_LEDGER_RELATIVE_PATH,
        STRUCTURE_MANIFEST_RELATIVE_PATH,
        DEPENDENCY_MANIFEST_RELATIVE_PATH,
    }:
        return False
    return path_text in USER_FACING_FILES or any(path_text.startswith(prefix) for prefix in USER_FACING_PREFIXES)


def _module_dir_exists(root: Path, module_name: str) -> bool:
    return (root / "src" / "fuggers_py" / module_name).exists()


def _extract_python_imports(path: Path) -> set[str]:
    try:
        tree = ast.parse(_read_text(path))
    except SyntaxError as exc:
        raise ValueError(f"{path.name} has invalid Python syntax: {exc.msg}.") from exc

    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def _extract_text_namespaces(path: Path) -> set[str]:
    return set(re.findall(r"fuggers_py(?:\.[A-Za-z_][A-Za-z0-9_]*)+", _read_text(path)))


def _changed_user_facing_namespaces(root: Path, delta_paths: set[str]) -> dict[str, set[str]]:
    namespaces: dict[str, set[str]] = {}
    for path_text in sorted(delta_paths):
        if not _path_is_user_facing(path_text):
            continue
        path = root / path_text
        if not path.exists():
            continue
        try:
            modules = _extract_python_imports(path) if path.suffix == ".py" else _extract_text_namespaces(path)
        except UnicodeDecodeError:
            continue
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        namespaces[path_text] = {module for module in modules if module.startswith("fuggers_py")}
    return namespaces


def _deep_import_errors(namespaces: dict[str, set[str]]) -> list[str]:
    errors: list[str] = []
    for path_text, modules in namespaces.items():
        for module in sorted(modules):
            for public_module in TARGET_PUBLIC_MODULES:
                if module.startswith(f"fuggers_py.{public_module}."):
                    errors.append(
                        f"{path_text} uses deep public import `{module}`. "
                        f"Use one-layer imports from `fuggers_py.{public_module}` instead."
                    )
    return errors


def _legacy_import_errors(root: Path, namespaces: dict[str, set[str]]) -> list[str]:
    errors: list[str] = []
    for old_path, new_path in LEGACY_IMPORT_REPLACEMENTS.items():
        new_module_name = new_path.removeprefix("fuggers_py.")
        if not _module_dir_exists(root, new_module_name):
            continue
        for path_text, modules in namespaces.items():
            for module in sorted(modules):
                if module == old_path or module.startswith(old_path + "."):
                    errors.append(
                        f"{path_text} still imports `{module}` after `{new_path}` exists. "
                        f"Use `{new_path}` instead."
                    )
    return errors


def _mapped_target_module_for_path(path_text: str) -> str | None:
    for prefix, module_name in LEGACY_PUBLIC_PATH_REPLACEMENTS.items():
        if path_text.startswith(prefix):
            return module_name
    return None


def _parse_tree(path: Path, *, root: Path) -> ast.Module:
    try:
        return ast.parse(_read_text(path))
    except SyntaxError as exc:
        relative_path = str(path.relative_to(root))
        raise ValueError(f"{relative_path} has invalid Python syntax: {exc.msg}.") from exc


def _imported_modules_from_tree(tree: ast.AST) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
    return imported


def _top_level_public_defs(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_") and node.name not in WRAPPER_ALLOWED_FUNCTIONS:
                names.add(node.name)
        elif isinstance(node, ast.FunctionDef):
            if not node.name.startswith("_") and node.name not in WRAPPER_ALLOWED_FUNCTIONS:
                names.add(node.name)
    return names


def _legacy_entrypoint_errors(root: Path, delta_paths: set[str]) -> list[str]:
    errors: list[str] = []
    for path_text in sorted(delta_paths):
        if not path_text.endswith("__init__.py"):
            continue
        target_module = _mapped_target_module_for_path(path_text)
        if target_module is None or not _module_dir_exists(root, target_module):
            continue
        path = root / path_text
        if not path.exists():
            continue
        tree = _parse_tree(path, root=root)
        imported_modules = _imported_modules_from_tree(tree)
        if any(
            module == f"fuggers_py.{target_module}" or module.startswith(f"fuggers_py.{target_module}.")
            for module in imported_modules
        ):
            errors.append(
                f"{path_text} preserves the old public path by re-exporting `fuggers_py.{target_module}`. "
                "This refactor is a hard rewrite. Remove the legacy public entrypoint instead of wrapping the new module."
            )
    return errors


def _wrapper_errors(root: Path, delta_paths: set[str]) -> list[str]:
    errors: list[str] = []
    for path_text in sorted(delta_paths):
        if not path_text.endswith(".py"):
            continue
        if not any(
            path_text.startswith(f"src/fuggers_py/{legacy_root}/")
            for legacy_root in (*LEGACY_PACKAGE_ROOTS, *DRAIN_BUCKETS)
        ):
            continue
        path = root / path_text
        if not path.exists():
            continue

        tree = _parse_tree(path, root=root)
        imported_modules = _imported_modules_from_tree(tree)

        if not any(
            module == f"fuggers_py.{public_module}" or module.startswith(f"fuggers_py.{public_module}.")
            for public_module in TARGET_PUBLIC_MODULES
            for module in imported_modules
        ):
            continue

        wrapper_like = True
        disallowed_defs: list[str] = []
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef)):
                disallowed_defs.append(node.name)
                wrapper_like = False
            elif isinstance(node, ast.FunctionDef) and node.name not in WRAPPER_ALLOWED_FUNCTIONS:
                disallowed_defs.append(node.name)
                wrapper_like = False

        if disallowed_defs:
            errors.append(
                f"{path_text} keeps compatibility logic in a legacy namespace: {', '.join(disallowed_defs)}. "
                "This refactor is a hard rewrite. Move the logic to the new public module and delete the old public path."
            )

        allowed_assignments = {"__all__"}
        for node in tree.body:
            if isinstance(node, ast.Assign):
                targets = {
                    target.id
                    for target in node.targets
                    if isinstance(target, ast.Name)
                }
                if not targets.issubset(allowed_assignments):
                    wrapper_like = False
                    errors.append(
                        f"{path_text} keeps compatibility state in a legacy namespace: "
                        f"{', '.join(sorted(targets))}. This refactor is a hard rewrite. Delete the old public path."
                    )
                    break
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.target.id not in allowed_assignments:
                    wrapper_like = False
                    errors.append(
                        f"{path_text} keeps compatibility state in a legacy namespace: "
                        f"{node.target.id}. This refactor is a hard rewrite. Delete the old public path."
                    )
                    break

        nonempty_lines = [
            line
            for line in _read_text(path).splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if len(nonempty_lines) > MAX_WRAPPER_NONEMPTY_LINES:
            wrapper_like = False
            errors.append(
                f"{path_text} keeps too much compatibility code in a legacy namespace ({len(nonempty_lines)} non-empty lines). "
                "This refactor is a hard rewrite. Delete the old public path instead."
            )
        if wrapper_like and not disallowed_defs:
            errors.append(
                f"{path_text} is a compatibility wrapper in a legacy namespace. "
                "This refactor is a hard rewrite. Delete the old public path instead of re-exporting the new module."
            )
    return errors


def _duplicate_move_errors(root: Path, delta_paths: set[str]) -> list[str]:
    errors: list[str] = []
    new_defs_by_module: dict[str, set[str]] = {module_name: set() for module_name in TARGET_PUBLIC_MODULES}

    for path_text in sorted(delta_paths):
        if not path_text.endswith(".py"):
            continue
        path = root / path_text
        if not path.exists():
            continue
        for module_name in TARGET_PUBLIC_MODULES:
            if path_text.startswith(f"src/fuggers_py/{module_name}/"):
                tree = _parse_tree(path, root=root)
                new_defs_by_module[module_name].update(_top_level_public_defs(tree))
                break

    for target_module, moved_defs in new_defs_by_module.items():
        if not moved_defs:
            continue
        for prefix, mapped_module in {**LEGACY_PUBLIC_PATH_REPLACEMENTS, **DRAIN_BUCKET_PATH_REPLACEMENTS}.items():
            if mapped_module != target_module:
                continue
            legacy_root = root / prefix
            if not legacy_root.exists():
                continue
            for legacy_path in sorted(legacy_root.rglob("*.py")):
                if "__pycache__" in legacy_path.parts:
                    continue
                tree = _parse_tree(legacy_path, root=root)
                overlap = sorted(_top_level_public_defs(tree) & moved_defs)
                if overlap:
                    errors.append(
                        f"{legacy_path.relative_to(root)} still defines moved symbols that now also exist under "
                        f"`fuggers_py.{target_module}`: {', '.join(overlap)}. "
                        "This refactor is a hard rewrite. Remove the old implementation."
                    )
    return errors


def _static_validation_errors(root: Path, delta_paths: set[str]) -> list[str]:
    namespaces = _changed_user_facing_namespaces(root, delta_paths)
    errors: list[str] = []
    errors.extend(_planning_change_set_errors(delta_paths))
    errors.extend(_canonical_public_dynamic_import_errors(root, delta_paths))
    errors.extend(_canonical_public_module_reassignment_errors(root, delta_paths))
    errors.extend(_canonical_public_drain_bucket_import_errors(root, delta_paths))
    errors.extend(_moved_phase1_symbol_import_errors(root, delta_paths))
    errors.extend(_core_self_contained_import_errors(root, delta_paths))
    errors.extend(_canonical_public_source_ownership_errors(root, delta_paths))
    errors.extend(_deep_import_errors(namespaces))
    errors.extend(_legacy_import_errors(root, namespaces))
    errors.extend(_legacy_entrypoint_errors(root, delta_paths))
    errors.extend(_wrapper_errors(root, delta_paths))
    errors.extend(_duplicate_move_errors(root, delta_paths))
    return errors


def _fast_validation_commands(root: Path, delta_paths: set[str]) -> list[list[str]]:
    commands: list[list[str]] = []
    changed_python = sorted(path for path in delta_paths if path.endswith(".py") and (root / path).exists())
    if changed_python:
        commands.append(["ruff", "check", *changed_python])

    tooling_sensitive = {
        ".codex/hooks.json",
        ".codex/agents/public_api_reviewer.toml",
        "pyproject.toml",
        CURRENT_INVENTORY_RELATIVE_PATH,
        EXPORT_MANIFEST_RELATIVE_PATH,
        LEGACY_DENYLIST_RELATIVE_PATH,
        MIGRATION_LEDGER_RELATIVE_PATH,
        STRUCTURE_MANIFEST_RELATIVE_PATH,
        DEPENDENCY_MANIFEST_RELATIVE_PATH,
        "tools/validate_public_api_refactor.py",
        "tests/contracts/tooling/test_public_api_current_inventory.py",
        "tests/contracts/tooling/test_public_api_phase1_slice2_controls.py",
        "tests/contracts/tooling/test_public_api_phase1_slice3_controls.py",
        "tests/contracts/tooling/test_public_api_refactor_validator.py",
    }
    if any(path_text in tooling_sensitive for path_text in delta_paths):
        commands.append(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/contracts/tooling/test_public_api_current_inventory.py",
                "tests/contracts/tooling/test_public_api_phase1_slice2_controls.py",
                "tests/contracts/tooling/test_public_api_phase1_slice3_controls.py",
                "tests/contracts/tooling/test_public_api_refactor_validator.py",
            ]
        )

    if any(_path_is_user_facing(path_text) for path_text in delta_paths):
        commands.append([sys.executable, "-m", "pytest", "-q", "tests/contracts/docs/test_docs_links.py"])

    return commands


def _full_validation_commands(root: Path, delta_paths: set[str]) -> list[list[str]]:
    commands = _fast_validation_commands(root, delta_paths)
    commands.extend(
        [
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/contracts/tooling/test_public_api_current_inventory.py",
                "tests/contracts/tooling/test_public_api_phase1_slice2_controls.py",
                "tests/contracts/tooling/test_public_api_phase1_slice3_controls.py",
                "tests/contracts/tooling/test_public_api_refactor_validator.py",
            ],
            [sys.executable, "-m", "pytest", "-q", "tests/contracts/docs"],
        ]
    )
    return commands


def validate_workflow(root: Path, *, run_commands: bool | ValidationCommandMode) -> ValidationResult:
    command_mode = _normalize_command_mode(run_commands)
    state = _ensure_state(root, create_if_missing=False)
    if not _workflow_is_active(state):
        return ValidationResult(
            False,
            "Public API refactor workflow is not active. Run `python tools/validate_public_api_refactor.py init` first.",
            [],
            None,
        )
    assert state is not None
    delta_paths = _delta_paths(root, state)
    fingerprint = _fingerprint_for_paths(root, delta_paths)
    if not delta_paths:
        return ValidationResult(True, None, ["No relevant refactor changes are pending."], None)

    details: list[str] = []
    inventory_error = _current_inventory_error(root)
    if inventory_error is not None:
        return ValidationResult(False, inventory_error, details, fingerprint)
    slice2_error = _slice2_control_files_error(root)
    if slice2_error is not None:
        return ValidationResult(False, slice2_error, details, fingerprint)
    slice3_error = _slice3_control_files_error(root)
    if slice3_error is not None:
        return ValidationResult(False, slice3_error, details, fingerprint)
    static_errors = _static_validation_errors(root, delta_paths)
    if static_errors:
        return ValidationResult(False, static_errors[0], details, fingerprint)
    slice3_exactness_error = _slice3_manifest_exactness_error(root)
    if slice3_exactness_error is not None:
        return ValidationResult(False, slice3_exactness_error, details, fingerprint)

    if command_mode == "none":
        return ValidationResult(True, None, details, fingerprint)

    commands = _fast_validation_commands(root, delta_paths) if command_mode == "checkpoint" else _full_validation_commands(root, delta_paths)
    for command in commands:
        completed = _run_shell(root, command)
        if completed.returncode != 0:
            joined = " ".join(command)
            stderr = completed.stderr.strip()
            stdout = completed.stdout.strip()
            snippet = (stderr or stdout or "No command output captured.").splitlines()[0]
            return ValidationResult(False, f"Validation command failed: `{joined}`. {snippet}", details, fingerprint)

    return ValidationResult(True, None, details, fingerprint)


def _review_artifact_error(root: Path, review_path: Path, fingerprint: str | None) -> str | None:
    if fingerprint is None:
        return None
    if not review_path.exists():
        return f"Missing reviewer artifact: {review_path.relative_to(root)}."
    text = _read_text(review_path)
    if "# public_api_reviewer" not in text:
        return "Reviewer artifact header must start with `# public_api_reviewer`."
    if "Workflow: public-api-refactor" not in text:
        return "Reviewer artifact must include `Workflow: public-api-refactor`."
    if f"Fingerprint: {fingerprint}" not in text:
        return "Reviewer artifact fingerprint does not match the current change set."
    if not re.search(r"^Status:\s*complete\s*$", text, flags=re.IGNORECASE | re.MULTILINE):
        return "Reviewer artifact must include `Status: complete`."
    if any(section not in text for section in REVIEW_REQUIRED_SECTIONS):
        return "Reviewer artifact is missing required sections."

    verdict_match = REVIEW_VERDICT_RE.search(text)
    if verdict_match is None:
        return "Reviewer artifact must include a verdict bullet."
    verdict = verdict_match.group(1).strip().lower()
    if verdict != "approve":
        return f"Reviewer verdict is `{verdict}`, not `approve`."
    return None


def complete_workflow(root: Path, *, review_path: Path, run_commands: bool | ValidationCommandMode) -> ValidationResult:
    result = validate_workflow(root, run_commands=run_commands)
    if not result.ok:
        return result

    review_error = _review_artifact_error(root, review_path, result.fingerprint)
    if review_error is not None:
        return ValidationResult(False, review_error, result.details, result.fingerprint)

    state = _ensure_state(root, create_if_missing=False)
    assert state is not None
    state["baseline_changed_paths"] = sorted(_relevant_paths(_current_changed_paths(root)))
    state["last_validation_ok"] = True
    state["last_validation_reason"] = None
    state["last_validated_fingerprint"] = None
    state["last_validated_at"] = _now_iso()
    state["last_reviewed_fingerprint"] = None
    state["last_reviewed_at"] = _now_iso()
    state["last_completed_at"] = _now_iso()
    _save_state(root, state)
    return result


def _mark_validation_state(
    root: Path,
    *,
    ok: bool,
    reason: str | None,
    fingerprint: str | None,
    reviewed: bool = False,
) -> None:
    state = _ensure_state(root, create_if_missing=False)
    if state is None:
        return
    state["last_validation_ok"] = ok
    state["last_validation_reason"] = reason
    state["last_validated_fingerprint"] = fingerprint
    state["last_validated_at"] = _now_iso()
    if reviewed:
        state["last_reviewed_fingerprint"] = fingerprint
        state["last_reviewed_at"] = _now_iso()
    _save_state(root, state)


def _status_message(root: Path) -> str:
    state = _load_state(root)
    if not _workflow_is_active(state):
        return (
            "Public API refactor workflow is not active. "
            "Start it with `python tools/validate_public_api_refactor.py init`."
        )
    assert state is not None
    delta_paths = _delta_paths(root, state)
    fingerprint = _fingerprint_for_paths(root, delta_paths)
    if not delta_paths:
        return "Public API refactor workflow is active. No pending public API refactor change set."

    lines = [
        f"Pending public API refactor change set: {len(delta_paths)} file(s).",
        f"Fingerprint: {fingerprint}",
    ]
    if state.get("last_validated_fingerprint") == fingerprint and state.get("last_validation_ok") is True:
        lines.append("Deterministic validation: passed for current fingerprint.")
    else:
        reason = state.get("last_validation_reason") or "Deterministic validation has not passed for this fingerprint."
        lines.append(f"Deterministic validation: {reason}")

    review_error = _review_artifact_error(root, _default_review_path(root), fingerprint)
    if review_error is None:
        lines.append("Reviewer artifact: fresh approve verdict present.")
    else:
        lines.append(f"Reviewer artifact: {review_error}")
    unchanged_dynamic_routers = {
        path_text: primitives
        for path_text, primitives in _canonical_public_dynamic_import_inventory(root).items()
        if path_text not in delta_paths
    }
    if unchanged_dynamic_routers:
        lines.append(
            "Canonical public router audit: "
            f"{len(unchanged_dynamic_routers)} entrypoint file(s) outside the current change set still use dynamic routing primitives."
        )
    return "\n".join(lines)


def _clear_state(root: Path) -> str:
    path = _state_path(root)
    path.unlink(missing_ok=True)
    try:
        path.parent.rmdir()
    except OSError:
        pass
    return "Cleared public API refactor workflow state."


def _handle_user_prompt_hook(root: Path) -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        payload = {}

    prompt = str(payload.get("prompt", ""))
    state = _load_state(root)
    active = _workflow_is_active(state)
    if not active and AUTO_ACTIVATE_TRIGGER_RE.search(prompt):
        state = init_workflow(root)
        active = True

    if not active:
        return 0
    assert state is not None
    delta_paths = _delta_paths(root, state)

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": (
                        "Public API refactor workflow is active for this repo. Use "
                        "`refactor/PUBLIC_API_TARGET_STATE.md` and `refactor/PUBLIC_API_REFACTOR_PLAN.md` as the "
                        "source of truth. Treat the older `CURVES_*` docs as historical context only. This is a hard "
                        "rewrite. Do not preserve backward compatibility, do not add compatibility wrappers, and do "
                        "not keep old public entrypoints alive once their replacement lands. Keep public imports one "
                        "layer deep. Execute the refactor one coherent slice at a time and do not mix multiple plan "
                        "slices in one change set. For a substantial slice, first gather symbol, dependency, test, "
                        "and docs impact for that slice, then implement the full slice, and only after the writing "
                        "step for the entire slice is complete hand the whole slice to review. Do not send "
                        "partial or micro-edit states to the reviewer. If review blocks, return to editing, fix the "
                        "slice, rerun checks, and rerun review until approved or concretely blocked. When code moves "
                        "to a new public module, remove the old public logic instead of re-exporting it. Do not "
                        "start the next slice until the current slice is validated, reviewed, and sealed. Before "
                        "finishing a change set, run "
                        "`python tools/validate_public_api_refactor.py validate`, spawn the read-only "
                        "`public_api_reviewer` subagent on `gpt-5.4` with `xhigh` reasoning, write "
                        "`artifacts/reviews/public_api_refactor.public_api_reviewer.md`, and finally run "
                        "`python tools/validate_public_api_refactor.py complete --review "
                        "artifacts/reviews/public_api_refactor.public_api_reviewer.md`. "
                        f"Current pending file count: {len(delta_paths)}."
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
    if not _workflow_is_active(state):
        return 0
    assert state is not None
    delta_paths = _delta_paths(root, state)
    if not delta_paths:
        return 0

    fingerprint = _fingerprint_for_paths(root, delta_paths)
    assert fingerprint is not None

    if state.get("last_validated_fingerprint") != fingerprint or state.get("last_validation_ok") is not True:
        message = (
            "Pending public API refactor change set is not validated for the current fingerprint. Run "
            "`python tools/validate_public_api_refactor.py validate` first."
        )
    else:
        review_error = _review_artifact_error(root, _default_review_path(root), fingerprint)
        if review_error is not None:
            message = (
                "Pending public API refactor change set does not have a fresh reviewer approval. "
                "Spawn `public_api_reviewer`, write "
                f"`{_default_review_path(root).relative_to(root)}`, then run "
                "`python tools/validate_public_api_refactor.py complete --review "
                "artifacts/reviews/public_api_refactor.public_api_reviewer.md`. "
                f"{review_error}"
            )
        else:
            message = (
                "Pending public API refactor change set is validated and reviewed but not sealed. Run "
                "`python tools/validate_public_api_refactor.py complete --review "
                "artifacts/reviews/public_api_refactor.public_api_reviewer.md`."
            )

    stop_hook_active = bool(payload.get("stop_hook_active"))
    if stop_hook_active:
        print(json.dumps({"continue": False, "stopReason": message, "systemMessage": message}))
        return 0
    print(json.dumps({"decision": "block", "reason": message}))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validator for the repo-local public API refactor workflow.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Activate the public API refactor workflow and reset its baseline to the current dirty tree.")

    validate_parser = subparsers.add_parser("validate", help="Validate the current public API refactor change set.")
    validate_parser.add_argument(
        "--full",
        action="store_true",
        help="Run the wider docs and tooling contract gate instead of the fast checkpoint gate.",
    )

    complete_parser = subparsers.add_parser(
        "complete",
        help="Validate the current change set, require reviewer approval, and advance the workflow baseline.",
    )
    complete_parser.add_argument(
        "--review",
        default=str(_default_review_path(ROOT).relative_to(ROOT)),
        help="Reviewer artifact path relative to the repo root.",
    )
    complete_parser.add_argument(
        "--full",
        action="store_true",
        help="Run the wider docs and tooling contract gate before sealing the change set.",
    )

    freeze_inventory_parser = subparsers.add_parser(
        "freeze-inventory",
        help="Freeze the current public and drain-list inventory for Phase 1 slice 1.",
    )
    freeze_inventory_parser.add_argument(
        "--output",
        default=CURRENT_INVENTORY_RELATIVE_PATH,
        help="Output path relative to the repo root.",
    )

    subparsers.add_parser(
        "freeze-export-controls",
        help="Freeze the export manifest, legacy denylist, and migration ledger for Phase 1 slice 2.",
    )
    subparsers.add_parser(
        "freeze-structure-controls",
        help="Freeze the structure manifest and dependency manifest for Phase 1 slice 3.",
    )

    subparsers.add_parser("status", help="Show the current public API refactor workflow state.")
    subparsers.add_parser("clear", help="Clear the public API refactor workflow state.")
    subparsers.add_parser("deactivate", help="Deactivate the public API refactor workflow without deleting the state file.")
    subparsers.add_parser("user-prompt-hook", help="Hook entrypoint used by Codex UserPromptSubmit hooks.")
    subparsers.add_parser("stop-hook", help="Hook entrypoint used by Codex Stop hooks.")

    args = parser.parse_args(argv)

    if args.command == "init":
        state = init_workflow(ROOT)
        print(
            "Activated public API refactor workflow with "
            f"{len(state['baseline_changed_paths'])} current relevant dirty path(s)."
        )
        return 0

    if args.command == "user-prompt-hook":
        return _handle_user_prompt_hook(ROOT)

    if args.command == "stop-hook":
        return _handle_stop_hook(ROOT)

    if args.command == "status":
        print(_status_message(ROOT))
        return 0

    if args.command == "clear":
        print(_clear_state(ROOT))
        return 0

    if args.command == "deactivate":
        print(deactivate_workflow(ROOT))
        return 0

    if args.command == "validate":
        command_mode: ValidationCommandMode = "completion" if args.full else "checkpoint"
        result = validate_workflow(ROOT, run_commands=command_mode)
        if not result.ok:
            _mark_validation_state(ROOT, ok=False, reason=result.reason, fingerprint=result.fingerprint)
            assert result.reason is not None
            print(result.reason)
            return 1
        reason = (
            "Full public API refactor validation passed. Run "
            "`python tools/validate_public_api_refactor.py complete --review "
            "artifacts/reviews/public_api_refactor.public_api_reviewer.md` to seal this change set."
            if args.full
            else "Checkpoint public API refactor validation passed."
        )
        _mark_validation_state(ROOT, ok=True, reason=reason, fingerprint=result.fingerprint)
        print(reason)
        return 0

    if args.command == "freeze-inventory":
        output_path = ROOT / args.output
        freeze_public_api_current_inventory(ROOT, output_path=output_path)
        print(f"Froze public API current inventory to {output_path.relative_to(ROOT)}.")
        return 0

    if args.command == "freeze-export-controls":
        written = freeze_public_api_export_controls(ROOT)
        joined = ", ".join(str(path.relative_to(ROOT)) for path in written)
        print(f"Froze public API export controls to {joined}.")
        return 0

    if args.command == "freeze-structure-controls":
        written = freeze_public_api_structure_controls(ROOT)
        joined = ", ".join(str(path.relative_to(ROOT)) for path in written)
        print(f"Froze public API structure controls to {joined}.")
        return 0

    review_path = ROOT / args.review
    command_mode = "completion" if args.full else "checkpoint"
    result = complete_workflow(ROOT, review_path=review_path, run_commands=command_mode)
    if not result.ok:
        _mark_validation_state(
            ROOT,
            ok=False,
            reason=result.reason,
            fingerprint=result.fingerprint,
            reviewed=_review_artifact_error(ROOT, review_path, result.fingerprint) is None,
        )
        assert result.reason is not None
        print(result.reason)
        return 1

    print("PASS: public API refactor change set is validated, reviewed, and sealed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
