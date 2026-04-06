from __future__ import annotations

import sys

import pytest

from tests.helpers._add_feature_validator import load_validator_module


@pytest.mark.feature_slug("validator-fast-checkpoints")
@pytest.mark.feature_category("properties")
def test_completion_commands_strictly_extend_checkpoint_commands() -> None:
    module = load_validator_module()
    feature_test_files = [
        "tests/integration/properties/test_feature_properties.py",
        "tests/integration/validation/test_feature_validation.py",
        "tests/unit/test_feature_unit.py",
    ]

    checkpoint_commands = module._validation_commands(
        feature_test_files,
        ["unit", "validation", "properties"],
        set(),
        command_mode="checkpoint",
    )
    completion_commands = module._validation_commands(
        feature_test_files,
        ["unit", "validation", "properties"],
        set(),
        command_mode="completion",
    )

    assert completion_commands[: len(checkpoint_commands)] == checkpoint_commands
    assert [sys.executable, "tools/source_coverage.py", "--pytest-args", "-q"] not in completion_commands
    assert ["mypy"] in completion_commands
    assert ["pytest", "-q", "tests/unit"] in completion_commands
    assert ["pytest", "-q"] not in completion_commands
    assert len(completion_commands) > len(checkpoint_commands)
