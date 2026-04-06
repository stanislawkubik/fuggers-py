from __future__ import annotations

import pytest

from tests.helpers._add_feature_validator import load_validator_module


@pytest.mark.feature_slug("validator-fast-checkpoints")
@pytest.mark.feature_category("unit")
def test_checkpoint_commands_only_run_feature_owned_tests() -> None:
    module = load_validator_module()
    feature_test_files = [
        "tests/integration/properties/test_feature_properties.py",
        "tests/integration/validation/test_feature_validation.py",
        "tests/unit/test_feature_unit.py",
    ]

    commands = module._validation_commands(
        feature_test_files,
        ["unit", "validation", "properties"],
        set(),
        command_mode="checkpoint",
    )

    assert commands == [["pytest", "-q", *feature_test_files]]

