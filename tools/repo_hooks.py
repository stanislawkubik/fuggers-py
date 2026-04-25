from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import re
import subprocess
import sys
from typing import Any
from pathlib import Path

from validate_api_cleanliness import validate_api_cleanliness
from validate_docs_coverage import validate_docs_coverage
from validate_public_api_surface import (
    validate_public_api_surface,
    validate_public_api_surface_contract_permission,
)
from validate_public_api_surface import write_public_api_surface_intent

ROOT = Path(__file__).resolve().parents[1]
TURN_STATE_PATH = ROOT / ".tmp" / "repo_hooks" / "turn_state.json"
PUBLIC_API_MODULE_PATHS = {
    "src/fuggers_py/__init__.py",
    "src/fuggers_py/bonds/__init__.py",
    "src/fuggers_py/credit/__init__.py",
    "src/fuggers_py/curves/__init__.py",
    "src/fuggers_py/funding/__init__.py",
    "src/fuggers_py/inflation/__init__.py",
    "src/fuggers_py/portfolio/__init__.py",
    "src/fuggers_py/rates/__init__.py",
    "src/fuggers_py/vol_surfaces/__init__.py",
}
PUBLIC_API_SURFACE_INTENT_RE = re.compile(
    r"\b("
    r"update public api surface|"
    r"accept public api change|"
    r"add public api export|"
    r"remove public api export|"
    r"change public api"
    r")\b",
    flags=re.IGNORECASE,
)
PUBLIC_API_SURFACE_NEGATION_RE = re.compile(
    r"\b(do not|don't|dont|no)\b.{0,80}\b(update public api surface|accept public api change|change public api)\b",
    flags=re.IGNORECASE,
)
PUBLIC_API_SURFACE_CONTEXT = (
    "The user explicitly allowed a public API surface change. You may update "
    "`specs/public_api_surface.json` only for the requested public API change. "
    "Do not update that contract to hide accidental exports. Update matching API tests and docs when needed, then run "
    "`python tools/validate_api_cleanliness.py` and `python tools/validate_public_api_surface.py`."
)
GENERAL_REPO_STANDARDS_CONTEXT = (
    "Repo standards for `src/` and public API edits:\n"
    "- Keep public imports one layer deep under the current first-layer modules: "
    "`fuggers_py`, `bonds`, `credit`, `curves`, `funding`, `inflation`, `portfolio`, `rates`, and `vol_surfaces`.\n"
    "- Do not add compatibility aliases, `sys.modules` shims, forwarding modules, or dynamic import wrappers to keep old paths alive.\n"
    "- Public exports must be explicit literal `__all__` entries. If a public export changes, update the matching API tests and `docs/api/*.md` page.\n"
    "- Update `specs/public_api_surface.json` only when the user explicitly asks to update or accept a public API surface change.\n"
    "- Source shape changes need matching structure docs when they add, delete, or rename modules. Docs and examples should use targeted checks, not the full source validation path."
)


def _run_tool(command: list[str], *, stdin_text: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        input=stdin_text,
        capture_output=True,
        text=True,
        check=False,
    )


def _git_output(command: list[str]) -> list[str]:
    completed = _run_tool(command)
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _current_changed_paths() -> set[str]:
    changed = set(_git_output(["git", "diff", "--name-only", "--relative", "HEAD"]))
    changed.update(_git_output(["git", "diff", "--name-only", "--relative", "--cached", "HEAD"]))
    changed.update(_git_output(["git", "ls-files", "--others", "--exclude-standard"]))
    return changed


def _current_path_status() -> dict[str, str]:
    status: dict[str, str] = {}
    for line in _git_output(["git", "diff", "--name-status", "--relative", "HEAD"]):
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status_code = parts[0][0]
        path = parts[-1]
        status[path] = status_code
    for path in _git_output(["git", "ls-files", "--others", "--exclude-standard"]):
        status[path] = "A"
    return status


def _has_source_changes(paths: set[str]) -> bool:
    return any(path.startswith("src/") for path in paths)


def _touches_public_api_surface(paths: set[str]) -> bool:
    return "specs/public_api_surface.json" in paths or any(path in PUBLIC_API_MODULE_PATHS for path in paths)


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _path_fingerprint(relative_path: str) -> str:
    path = ROOT / relative_path
    if not path.exists():
        return "<missing>"
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _current_changed_snapshot() -> dict[str, str]:
    return {path: _path_fingerprint(path) for path in sorted(_current_changed_paths())}


def _write_turn_state(prompt: str) -> None:
    TURN_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": _now_iso(),
        "prompt": prompt,
        "changed_snapshot": _current_changed_snapshot(),
    }
    TURN_STATE_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_turn_state() -> dict[str, Any]:
    if not TURN_STATE_PATH.exists():
        return {}
    try:
        payload = json.loads(TURN_STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _turn_changed_paths() -> set[str]:
    payload = _read_turn_state()
    baseline = payload.get("changed_snapshot")
    if not isinstance(baseline, dict):
        return _current_changed_paths()
    baseline_snapshot = {str(path): str(fingerprint) for path, fingerprint in baseline.items()}
    current_snapshot = _current_changed_snapshot()
    paths = set(baseline_snapshot) | set(current_snapshot)
    return {path for path in paths if current_snapshot.get(path) != baseline_snapshot.get(path)}


def _turn_path_status(paths: set[str]) -> dict[str, str]:
    payload = _read_turn_state()
    baseline = payload.get("changed_snapshot")
    baseline_snapshot = {str(path): str(fingerprint) for path, fingerprint in baseline.items()} if isinstance(baseline, dict) else {}
    current_status = _current_path_status()
    path_status: dict[str, str] = {}
    for path in sorted(paths):
        if path in baseline_snapshot:
            path_status[path] = "D" if _path_fingerprint(path) == "<missing>" else "M"
        else:
            path_status[path] = current_status.get(path, "M")
    return path_status


def _block_payload(message: str, *, stop_hook_active: bool) -> dict[str, object]:
    if stop_hook_active:
        return {
            "continue": False,
            "stopReason": message,
            "systemMessage": message,
        }
    return {
        "decision": "block",
        "reason": message,
    }


def _read_json(raw: str) -> dict[str, object]:
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


def _print_passthrough_output(completed: subprocess.CompletedProcess[str]) -> bool:
    output = completed.stdout.strip()
    if output:
        print(output)
        return True
    return False


def _format_gate_failure(title: str, errors: list[str]) -> str:
    lines = [title, ""]
    lines.extend(f"- {error}" for error in errors)
    return "\n".join(lines)


def _block_if_failed(
    result: object,
    *,
    title: str,
    stop_hook_active: bool,
) -> bool:
    ok = bool(getattr(result, "ok", False))
    if ok:
        return False
    errors = getattr(result, "errors", None)
    if isinstance(errors, list) and errors:
        message = _format_gate_failure(title, [str(error) for error in errors])
    else:
        reason = getattr(result, "reason", None)
        message = str(reason or title)
    print(json.dumps(_block_payload(message, stop_hook_active=stop_hook_active)))
    return True


def _public_api_surface_intent_requested(prompt: str) -> bool:
    if PUBLIC_API_SURFACE_NEGATION_RE.search(prompt):
        return False
    return bool(PUBLIC_API_SURFACE_INTENT_RE.search(prompt))


def _hook_context_payload(context: str) -> dict[str, object]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }


def _prompt_hook_payload(completed: subprocess.CompletedProcess[str]) -> dict[str, object] | None:
    output = completed.stdout.strip()
    if not output:
        return None
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        print(output)
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _prompt_hook_context(payload: dict[str, object]) -> str | None:
    hook_output = payload.get("hookSpecificOutput")
    if not isinstance(hook_output, dict):
        return None
    context = hook_output.get("additionalContext")
    return context if isinstance(context, str) and context.strip() else None


def _run_add_feature_hook(command: str, raw_stdin: str) -> subprocess.CompletedProcess[str]:
    return _run_tool(
        [sys.executable, str(ROOT / "tools" / "validate_add_feature.py"), command],
        stdin_text=raw_stdin,
    )


def handle_user_prompt_hook(raw_stdin: str) -> int:
    payload = _read_json(raw_stdin)
    prompt = str(payload.get("prompt", ""))
    _write_turn_state(prompt)
    prompt_contexts: list[str] = [GENERAL_REPO_STANDARDS_CONTEXT]
    if _public_api_surface_intent_requested(prompt):
        write_public_api_surface_intent(ROOT, prompt=prompt)
        prompt_contexts.append(PUBLIC_API_SURFACE_CONTEXT)

    add_feature = _run_add_feature_hook("user-prompt-hook", raw_stdin)
    add_feature_payload = _prompt_hook_payload(add_feature)
    if add_feature_payload is not None and "decision" in add_feature_payload:
        print(json.dumps(add_feature_payload))
        return 0
    if add_feature.returncode != 0:
        message = (add_feature.stderr or add_feature.stdout).strip() or "add-feature prompt hook failed."
        print(json.dumps({"decision": "block", "reason": message}))
        return 0
    if add_feature_payload is not None:
        context = _prompt_hook_context(add_feature_payload)
        if context is not None:
            prompt_contexts.append(context)

    if prompt_contexts:
        print(json.dumps(_hook_context_payload("\n\n".join(prompt_contexts))))
    return 0


def handle_stop_hook(raw_stdin: str) -> int:
    payload = _read_json(raw_stdin)
    stop_hook_active = bool(payload.get("stop_hook_active"))

    add_feature = _run_add_feature_hook("stop-hook", raw_stdin)
    if _print_passthrough_output(add_feature):
        return 0
    if add_feature.returncode != 0:
        message = (add_feature.stderr or add_feature.stdout).strip() or "add-feature stop hook failed."
        print(json.dumps(_block_payload(message, stop_hook_active=stop_hook_active)))
        return 0

    changed_paths = _turn_changed_paths()
    if not changed_paths:
        return 0

    path_status = _turn_path_status(changed_paths)
    docs_coverage = validate_docs_coverage(ROOT, path_status=path_status)
    if _block_if_failed(docs_coverage, title="Docs coverage failed.", stop_hook_active=stop_hook_active):
        return 0

    if not _has_source_changes(changed_paths):
        return 0

    api_cleanliness = validate_api_cleanliness(ROOT, paths=changed_paths)
    if _block_if_failed(api_cleanliness, title="API cleanliness failed.", stop_hook_active=stop_hook_active):
        return 0

    if not _touches_public_api_surface(changed_paths):
        return 0

    api_surface = validate_public_api_surface(ROOT)
    if _block_if_failed(api_surface, title="Public API surface changed.", stop_hook_active=stop_hook_active):
        return 0

    api_surface_permission = validate_public_api_surface_contract_permission(ROOT)
    _block_if_failed(
        api_surface_permission,
        title="Public API surface contract permission failed.",
        stop_hook_active=stop_hook_active,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Repo-local hook router.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("user-prompt-hook", help="Prompt hook entrypoint.")
    subparsers.add_parser("stop-hook", help="Stop hook entrypoint.")
    args = parser.parse_args(argv)

    raw_stdin = sys.stdin.read()
    if args.command == "user-prompt-hook":
        return handle_user_prompt_hook(raw_stdin)
    if args.command == "stop-hook":
        return handle_stop_hook(raw_stdin)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
