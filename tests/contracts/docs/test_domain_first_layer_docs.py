from __future__ import annotations

from tests.helpers._paths import REPO_ROOT


ROOT = REPO_ROOT
DOMAIN_DOCS = (
    "docs/api/bonds.md",
    "docs/api/rates.md",
    "docs/api/inflation.md",
    "docs/api/credit.md",
    "docs/api/funding.md",
)


def test_domain_first_layer_docs_exist_and_are_listed_in_api_index() -> None:
    index_text = (ROOT / "docs/api/index.md").read_text(encoding="utf-8")

    for relative_path in DOMAIN_DOCS:
        assert (ROOT / relative_path).exists()
        page_name = relative_path.rsplit("/", maxsplit=1)[-1].removesuffix(".md")
        assert f"\n{page_name}\n" in index_text

    for old_page_name in ("reference", "products", "pricers", "measures", "calc", "adapters"):
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


def test_reference_page_is_legacy_and_points_to_root_or_domain_imports() -> None:
    text = (ROOT / "docs/api/reference.md").read_text(encoding="utf-8")

    assert "Retired public namespace." in text
    assert "no longer part of the public API" in text
    assert "from fuggers_py import (" in text
    assert "from fuggers_py.bonds import YieldCalculationRules" in text
    assert "from fuggers_py.inflation import USD_CPI_U_NSA" in text
    assert "from fuggers_py.rates import IndexConventions, OvernightCompounding" in text
    assert ".. automodule:: fuggers_py.reference" not in text


def test_calc_and_adapters_pages_are_legacy_infrastructure_notes() -> None:
    calc_text = (ROOT / "docs/api/calc.md").read_text(encoding="utf-8")
    adapters_text = (ROOT / "docs/api/adapters.md").read_text(encoding="utf-8")

    assert "Retired public namespace." in calc_text
    assert "no longer part of the public API" in calc_text
    assert "from fuggers_py.bonds import FixedBondBuilder" in calc_text
    assert ".. automodule:: fuggers_py.calc" not in calc_text

    assert "Retired public namespace." in adapters_text
    assert "no longer part of the public API" in adapters_text
    assert "_storage" in adapters_text
    assert ".. automodule:: fuggers_py.adapters" not in adapters_text


def test_readme_keeps_internal_roots_out_of_main_package_layout() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "- `fuggers_py.core`:" not in text
    assert "- `fuggers_py.math`:" not in text
    assert "- `fuggers_py.calc`:" not in text
    assert "- `fuggers_py.adapters`:" not in text
    assert "Internal implementation roots such as `_core`, `_math`, `_market`, `_calc`" in text
