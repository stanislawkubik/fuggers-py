from __future__ import annotations

from tests.helpers._paths import REPO_ROOT


ROOT = REPO_ROOT


def test_curve_and_surface_docs_use_first_layer_public_paths() -> None:
    canonical_paths = (
        "docs/api/curves.md",
        "docs/api/vol_surfaces.md",
        "docs/api/market.md",
        "docs/api/index.md",
        "docs/api/market_curves.md",
        "docs/SRC_STRUCTURE.md",
        "examples/README.md",
    )
    banned = (
        "fuggers_py.market.curves",
        "fuggers_py.market.vol_surfaces",
        "market/curves/",
        "market/vol_surfaces/",
        "market_curves.md",
    )

    for relative_path in canonical_paths:
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        for banned_text in banned:
            assert banned_text not in text, f"{relative_path} still mentions {banned_text!r}"


def test_new_first_layer_curve_and_surface_docs_exist() -> None:
    assert (ROOT / "docs/api/curves.md").exists()
    assert (ROOT / "docs/api/vol_surfaces.md").exists()
    assert (ROOT / "docs/api/market_curves.md").exists()


def test_example_notebooks_do_not_spell_the_old_curve_and_surface_public_paths() -> None:
    banned = (
        "fuggers_py.market.curves",
        "fuggers_py.market.vol_surfaces",
        "fuggers_py.market.quotes",
        "fuggers_py.measures.",
        "fuggers_py.pricers.",
        "fuggers_py.products.",
    )

    for notebook_path in sorted((ROOT / "examples").glob("*.ipynb")):
        text = notebook_path.read_text(encoding="utf-8")
        for banned_text in banned:
            assert banned_text not in text, f"{notebook_path.relative_to(ROOT)} still mentions {banned_text!r}"


def test_structure_doc_points_curve_and_surface_internals_to_internal_packages() -> None:
    text = (ROOT / "docs/SRC_STRUCTURE.md").read_text(encoding="utf-8")

    assert "_curves_impl/" not in text
    assert "curves/" in text
    assert "_vol_surfaces_impl/" not in text
    assert "_market/curve_support.py" not in text
    assert "curves/date_support.py" in text
    assert "vol_surfaces/" in text
