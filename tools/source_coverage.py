from __future__ import annotations

import argparse
import json
import os
import pickle
import signal
import subprocess
import sys
import sysconfig
import tempfile
import threading
import time
import tomllib
import trace
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"


@dataclass(frozen=True, slots=True)
class FileCoverage:
    path: str
    package: str
    covered_lines: int
    executable_lines: int

    @property
    def percent(self) -> float:
        if self.executable_lines == 0:
            return 100.0
        return 100.0 * self.covered_lines / self.executable_lines


def _load_config() -> dict[str, Any]:
    with PYPROJECT.open("rb") as handle:
        data = tomllib.load(handle)
    return data["tool"]["fuggers_source_coverage"]


def _should_omit(path: Path, omit_globs: list[str]) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return any(fnmatch(rel, pattern) for pattern in omit_globs)


def _package_name(path: Path) -> str:
    parts = path.relative_to(ROOT / "src" / "fuggers_py").parts
    if not parts:
        return "fuggers_py"
    if parts[0].endswith(".py"):
        return "fuggers_py"
    return parts[0]


def _iter_source_files(source_roots: list[str], omit_globs: list[str]) -> list[Path]:
    files: list[Path] = []
    for root_text in source_roots:
        root = ROOT / root_text
        for path in sorted(root.rglob("*.py")):
            if _should_omit(path, omit_globs):
                continue
            files.append(path.resolve())
    return files


def _trace_ignoredirs() -> list[str]:
    candidates = {
        sys.prefix,
        sys.exec_prefix,
        sys.base_prefix,
        sys.base_exec_prefix,
        sysconfig.get_paths().get("stdlib"),
        sysconfig.get_paths().get("platstdlib"),
        sysconfig.get_paths().get("purelib"),
        sysconfig.get_paths().get("platlib"),
    }
    return [value for value in candidates if value]


def _raise_interrupt(_signum: int, _frame: Any) -> None:
    raise KeyboardInterrupt


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _run_child_measurement(
    *,
    counts_output: Path,
    coverage_workdir: Path,
    parent_pid: int | None,
    pytest_args: list[str],
) -> int:
    import pytest

    ignoredirs = tuple(str(Path(path).resolve()) for path in _trace_ignoredirs())
    counts: dict[tuple[str, int], int] = {}

    def tracer(frame, event, arg):
        if event == "line":
            filename = frame.f_code.co_filename
            try:
                resolved = str(Path(filename).resolve())
            except Exception:
                resolved = str(Path(filename).absolute())
            if resolved.endswith(".py") and not any(resolved.startswith(path) for path in ignoredirs):
                key = (resolved, frame.f_lineno)
                counts[key] = counts.get(key, 0) + 1
        return tracer

    if parent_pid is not None:
        def parent_watcher() -> None:
            while True:
                if os.getppid() != parent_pid:
                    os._exit(2)
                time.sleep(0.5)

        watcher = threading.Thread(target=parent_watcher, name="source-coverage-parent-watcher", daemon=True)
        watcher.start()

    coverage_workdir.mkdir(parents=True, exist_ok=True)
    previous_trace = sys.gettrace()
    previous_threading_trace = threading.gettrace()
    sys.settrace(tracer)
    threading.settrace(tracer)
    try:
        exit_code = int(pytest.main(pytest_args))
    finally:
        sys.settrace(previous_trace)
        threading.settrace(previous_threading_trace)
    counts_output.write_bytes(pickle.dumps((counts, {}, {}), protocol=1))
    return exit_code


def _measure(pytest_args: list[str]) -> tuple[int, dict[tuple[str, int], int]]:
    with tempfile.TemporaryDirectory(prefix="fuggers-source-coverage-") as tmpdir:
        tmp_root = Path(tmpdir)
        counts_output = tmp_root / "counts.pkl"
        coverage_workdir = tmp_root / "cover"
        cmd = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--counts-output",
            str(counts_output),
            "--coverage-workdir",
            str(coverage_workdir),
            "--parent-pid",
            str(os.getpid()),
            "--pytest-args",
            *(pytest_args or ["-q"]),
        ]
        completed = subprocess.Popen(cmd, cwd=ROOT)
        previous_handlers: dict[int, Any] = {}
        for handled_signal in (signal.SIGINT, signal.SIGTERM):
            previous_handlers[handled_signal] = signal.getsignal(handled_signal)
            signal.signal(handled_signal, _raise_interrupt)
        try:
            exit_code = int(completed.wait())
        except BaseException:
            _stop_process(completed)
            raise
        finally:
            for handled_signal, previous_handler in previous_handlers.items():
                signal.signal(handled_signal, previous_handler)
        if not counts_output.exists():
            raise RuntimeError("Source coverage child run did not produce a counts file.")
        counts, _calledfuncs, _callers = pickle.loads(counts_output.read_bytes())
        return exit_code, counts


def _normalize_counts(raw_counts: dict[tuple[str, int], int]) -> dict[tuple[str, int], int]:
    normalized: dict[tuple[str, int], int] = {}
    for (filename, lineno), count in raw_counts.items():
        try:
            resolved = str(Path(filename).resolve())
        except Exception:
            resolved = str(Path(filename).absolute())
        normalized[(resolved, lineno)] = normalized.get((resolved, lineno), 0) + count
    return normalized


def _file_coverage(path: Path, counts: dict[tuple[str, int], int]) -> FileCoverage:
    executable = trace._find_executable_linenos(str(path))
    covered = sum(1 for line in executable if counts.get((str(path), line), 0) > 0)
    return FileCoverage(
        path=str(path.relative_to(ROOT)),
        package=_package_name(path),
        covered_lines=covered,
        executable_lines=len(executable),
    )


def _aggregate(files: list[FileCoverage], packages: list[str]) -> dict[str, Any]:
    overall_hits = sum(item.covered_lines for item in files)
    overall_lines = sum(item.executable_lines for item in files)
    overall_percent = 100.0 if overall_lines == 0 else 100.0 * overall_hits / overall_lines
    by_package: dict[str, dict[str, Any]] = {}
    for package in packages:
        selected = [item for item in files if item.package == package]
        hits = sum(item.covered_lines for item in selected)
        lines = sum(item.executable_lines for item in selected)
        percent = 100.0 if lines == 0 else 100.0 * hits / lines
        by_package[package] = {
            "covered_lines": hits,
            "executable_lines": lines,
            "coverage_percent": percent,
        }
    return {
        "overall": {
            "covered_lines": overall_hits,
            "executable_lines": overall_lines,
            "coverage_percent": overall_percent,
        },
        "packages": by_package,
    }


def _report_text(summary: dict[str, Any], thresholds: dict[str, float]) -> str:
    lines = [
        f"Overall: {summary['overall']['coverage_percent']:.2f}% "
        f"({summary['overall']['covered_lines']}/{summary['overall']['executable_lines']}) "
        f"[min {thresholds['overall']:.2f}%]"
    ]
    for package, values in summary["packages"].items():
        lines.append(
            f"{package}: {values['coverage_percent']:.2f}% "
            f"({values['covered_lines']}/{values['executable_lines']}) "
            f"[min {thresholds['package']:.2f}%]"
        )
    return "\n".join(lines)


def _enforce(summary: dict[str, Any], *, overall_min: float, package_min: float) -> list[str]:
    failures: list[str] = []
    if summary["overall"]["coverage_percent"] < overall_min:
        failures.append(
            f"overall coverage {summary['overall']['coverage_percent']:.2f}% is below {overall_min:.2f}%"
        )
    for package, values in summary["packages"].items():
        if values["coverage_percent"] < package_min:
            failures.append(
                f"{package} coverage {values['coverage_percent']:.2f}% is below {package_min:.2f}%"
            )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Source-only coverage runner built on stdlib trace.")
    parser.add_argument(
        "--counts-output",
        type=Path,
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--coverage-workdir",
        type=Path,
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Optional JSON output path for the computed source coverage summary.",
    )
    parser.add_argument(
        "--parent-pid",
        type=int,
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--pytest-args",
        nargs=argparse.REMAINDER,
        default=["-q"],
        help="Arguments forwarded to pytest after '--pytest-args'.",
    )
    args = parser.parse_args(argv)

    if args.counts_output is not None:
        if args.coverage_workdir is None:
            raise SystemExit("--coverage-workdir is required when --counts-output is provided.")
        return _run_child_measurement(
            counts_output=args.counts_output,
            coverage_workdir=args.coverage_workdir,
            parent_pid=args.parent_pid,
            pytest_args=args.pytest_args or ["-q"],
        )

    config = _load_config()
    source_files = _iter_source_files(config["source"], config.get("omit_globs", []))
    exit_code, raw_counts = _measure(args.pytest_args or ["-q"])
    normalized_counts = _normalize_counts(raw_counts)
    file_results = [_file_coverage(path, normalized_counts) for path in source_files]
    summary = _aggregate(file_results, config["measured_packages"])
    payload = {
        "pytest_exit_code": exit_code,
        "summary": summary,
        "files": [
            {
                "path": item.path,
                "package": item.package,
                "covered_lines": item.covered_lines,
                "executable_lines": item.executable_lines,
                "coverage_percent": item.percent,
            }
            for item in file_results
        ],
    }

    print(
        _report_text(
            summary,
            {"overall": float(config["overall_min"]), "package": float(config["package_min"])},
        )
    )

    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    failures = _enforce(
        summary,
        overall_min=float(config["overall_min"]),
        package_min=float(config["package_min"]),
    )
    if exit_code != 0:
        return exit_code
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
