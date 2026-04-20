from __future__ import annotations

from tests.helpers._paths import REPO_ROOT


ROOT = REPO_ROOT
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
BANNED_PUBLIC_STORY_IMPORTS = (
    "fuggers_py.market.",
    "fuggers_py.market.curves",
    "fuggers_py.market.vol_surfaces",
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
