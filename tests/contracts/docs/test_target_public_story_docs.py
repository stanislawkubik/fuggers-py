from __future__ import annotations

from tests.helpers._paths import REPO_ROOT


ROOT = REPO_ROOT
MARKET_CURVES = "fuggers_py.market." + "curves"
MARKET_VOL_SURFACES = "fuggers_py.market." + "vol_surfaces"
TARGET_PUBLIC_STORY_DOCS = (
    "docs/api/index.md",
    "docs/api/curves.md",
    "docs/api/vol_surfaces.md",
    "docs/api/bonds.md",
    "docs/api/rates.md",
    "docs/api/inflation.md",
    "docs/api/credit.md",
    "docs/api/funding.md",
    "docs/api/portfolio.md",
    "examples/README.md",
)
RELEASE_STATE_DOCS = (
    "README.md",
    "CHANGELOG.md",
    "docs/STATUS.md",
    "docs/validation_strategy.md",
    "docs/dev/internal_modules.md",
)
BANNED_PUBLIC_STORY_IMPORTS = (
    "fuggers_py.market.",
    MARKET_CURVES,
    MARKET_VOL_SURFACES,
    "fuggers_py.market.quotes",
    "fuggers_py.products.",
    "fuggers_py.pricers.",
    "fuggers_py.measures.",
    "fuggers_py.reference.",
    "fuggers_py.calc.",
    "fuggers_py.adapters.",
    "fuggers_py.core",
    "fuggers_py.math",
    "fuggers_py.fixings",
    "fuggers_py.derivatives",
    "from fuggers_py.core import",
)
BANNED_AGENT_WORKFLOW_TERMS = (
    "Co" + "dex",
    "codex" + "_hooks",
    "public API refactor " + "workflow",
)


def test_target_public_story_docs_do_not_send_users_to_old_public_roots() -> None:
    for relative_path in TARGET_PUBLIC_STORY_DOCS:
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        for banned_text in BANNED_PUBLIC_STORY_IMPORTS:
            assert banned_text not in text, f"{relative_path} still mentions {banned_text!r}"


def test_api_index_keeps_the_main_story_on_first_layer_public_packages() -> None:
    text = (ROOT / "docs/api/index.md").read_text(encoding="utf-8")

    for page_name in (
        "curves",
        "vol_surfaces",
        "bonds",
        "rates",
        "inflation",
        "credit",
        "funding",
        "portfolio",
    ):
        assert f"\n{page_name}\n" in text

    for non_first_layer_page_name in (
        "core",
        "market",
        "math",
        "reference",
        "products",
        "pricers",
        "measures",
        "calc",
        "adapters",
        "quotes",
        "fixings",
        "derivatives",
    ):
        assert f"\n{non_first_layer_page_name}\n" not in text


def test_release_state_docs_do_not_describe_agent_specific_workflows() -> None:
    for relative_path in RELEASE_STATE_DOCS:
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        for banned_text in BANNED_AGENT_WORKFLOW_TERMS:
            assert banned_text not in text, f"{relative_path} still mentions {banned_text!r}"


def test_validation_strategy_keeps_hooks_secondary_to_shell_validators() -> None:
    text = (ROOT / "docs/validation_strategy.md").read_text(encoding="utf-8")

    assert "The validation commands are the source of truth." in text
    assert "hooks are optional wrappers, not the main validation surface" in text
    assert "separate source of rules" in text
    assert "python tools/repo_hooks.py stop-hook" in text


def test_publish_tree_does_not_ship_legacy_examples_or_duplicate_rtd_configs() -> None:
    assert not (ROOT / "artifacts/legacy_examples").exists()
    assert (ROOT / ".readthedocs.yaml").exists()
    assert not (ROOT / ".readthedocs.yml").exists()
