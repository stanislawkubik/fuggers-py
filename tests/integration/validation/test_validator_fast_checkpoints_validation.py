from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.helpers._add_feature_validator import init_complete_workflow


@pytest.mark.feature_slug("validator-fast-checkpoints")
@pytest.mark.feature_category("validation")
def test_validate_uses_checkpoint_commands_by_default(tmp_path: Path) -> None:
    module = init_complete_workflow(tmp_path, "validator-fast-checkpoints")
    commands: list[list[str]] = []
    original_run_shell = module._run_shell

    def fake_run_shell(root: Path, command: list[str]) -> subprocess.CompletedProcess[str]:
        if command[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(command, 1, "", "")
        if command and command[0] == "git":
            raise AssertionError(f"Unexpected git command during checkpoint validation: {command}")
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    try:
        module._run_shell = fake_run_shell
        result = module.validate_workflow(tmp_path, "validator-fast-checkpoints", run_commands="checkpoint")
    finally:
        module._run_shell = original_run_shell

    assert result.ok is True
    assert commands == [
        [
            "pytest",
            "-q",
            "tests/integration/properties/test_feature_properties.py",
            "tests/integration/validation/test_feature_validation.py",
            "tests/unit/test_feature_unit.py",
        ]
    ]
