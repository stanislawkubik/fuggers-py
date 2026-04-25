from __future__ import annotations

from tests.helpers._paths import REPO_ROOT


ROOT = REPO_ROOT
DOMAIN_DOCS = (
    "docs/api/curves.md",
    "docs/api/vol_surfaces.md",
    "docs/api/bonds.md",
    "docs/api/rates.md",
    "docs/api/inflation.md",
    "docs/api/credit.md",
    "docs/api/funding.md",
    "docs/api/portfolio.md",
)
RETIRED_PUBLIC_DOCS = (
    "docs/api/reference.md",
    "docs/api/products.md",
    "docs/api/pricers.md",
    "docs/api/measures.md",
    "docs/api/market.md",
    "docs/api/market_curves.md",
    "docs/api/calc.md",
    "docs/api/adapters.md",
)


def test_domain_first_layer_docs_exist_and_are_listed_in_api_index() -> None:
    index_text = (ROOT / "docs/api/index.md").read_text(encoding="utf-8")

    for relative_path in DOMAIN_DOCS:
        assert (ROOT / relative_path).exists()
        page_name = relative_path.rsplit("/", maxsplit=1)[-1].removesuffix(".md")
        assert f"\n{page_name}\n" in index_text

    for old_page_name in (
        "reference",
        "products",
        "pricers",
        "measures",
        "market",
        "market_curves",
        "calc",
        "adapters",
    ):
        assert f"\n{old_page_name}\n" not in index_text


def test_domain_first_layer_docs_do_not_point_users_back_to_old_public_layers() -> None:
    banned = (
        "fuggers_py.products.",
        "fuggers_py.pricers.",
        "fuggers_py.measures.",
        "fuggers_py.reference.",
        "fuggers_py.market.indices",
    )

    for relative_path in DOMAIN_DOCS:
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        for banned_text in banned:
            assert banned_text not in text, f"{relative_path} still mentions {banned_text!r}"


def test_retired_public_api_pages_are_removed() -> None:
    for relative_path in RETIRED_PUBLIC_DOCS:
        assert not (ROOT / relative_path).exists(), f"{relative_path} must not be a public API doc"


def test_readme_keeps_internal_roots_out_of_main_package_layout() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "- `fuggers_py.core`:" not in text
    assert "- `fuggers_py.math`:" not in text
    assert "- `fuggers_py.calc`:" not in text
    assert "- `fuggers_py.adapters`:" not in text
    assert "Internal implementation roots such as `_core`, `_math`, `_runtime`, and" in text
