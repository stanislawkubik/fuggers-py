from __future__ import annotations

import json

from tests.helpers._paths import REPO_ROOT


ROOT = REPO_ROOT
MARKET_CURVES = "fuggers_py.market." + "curves"
MARKET_VOL_SURFACES = "fuggers_py.market." + "vol_surfaces"
REMOVED_CURVE_BUCKET = "_curves" "_impl"
REMOVED_SURFACE_BUCKET = "_vol_surfaces" "_impl"


def test_curve_and_surface_docs_use_first_layer_public_paths() -> None:
    canonical_paths = (
        "docs/api/curves.md",
        "docs/api/vol_surfaces.md",
        "docs/api/index.md",
        "docs/SRC_STRUCTURE.md",
        "examples/README.md",
    )
    banned = (
        MARKET_CURVES,
        MARKET_VOL_SURFACES,
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
    assert not (ROOT / "docs/api/market.md").exists()
    assert not (ROOT / "docs/api/market_curves.md").exists()


def test_example_notebooks_do_not_spell_the_old_curve_and_surface_public_paths() -> None:
    banned = (
        MARKET_CURVES,
        MARKET_VOL_SURFACES,
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

    assert f"{REMOVED_CURVE_BUCKET}/" not in text
    assert "curves/" in text
    assert f"{REMOVED_SURFACE_BUCKET}/" not in text
    assert "_market/curve_support.py" not in text
    assert "curves/date_support.py" in text
    assert "vol_surfaces/" in text


def test_first_curve_docs_and_example_use_default_fit_path() -> None:
    docs_text = (ROOT / "docs/api/curves.md").read_text(encoding="utf-8")
    basic_fit = docs_text.split("## Basic Fit", 1)[1].split("## `CurveSpec`", 1)[0]
    assert "YieldCurve.fit(" in basic_fit
    assert "kernel=" not in basic_fit
    assert "method=" not in basic_fit

    notebook = json.loads((ROOT / "examples/01_treasury_curve_fit.ipynb").read_text(encoding="utf-8"))
    source = "\n".join(
        "".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"
    )
    curve_example = source.split("spline_no_regressors = YieldCurve.fit", 1)[0]
    assert "YieldCurve.fit(" in curve_example
    assert "kernel=" not in curve_example
    assert "method=" not in curve_example


def test_curve_static_docs_do_not_mention_removed_report_types() -> None:
    removed_report_names = ("GlobalFitReport", "GlobalFitPoint")

    for path in sorted((ROOT / "docs" / "_static" / "api").glob("*.svg")):
        text = path.read_text(encoding="utf-8")
        for removed_name in removed_report_names:
            assert removed_name not in text, f"{path.relative_to(ROOT)} still mentions {removed_name}"


def test_curve_docs_do_not_render_raw_sphinx_api_reference() -> None:
    text = (ROOT / "docs/api/curves.md").read_text(encoding="utf-8")

    assert ".. automodule::" not in text
    assert "## API Reference" not in text


def test_curve_docs_identify_advanced_imports_and_work_in_progress() -> None:
    text = (ROOT / "docs/api/curves.md").read_text(encoding="utf-8")

    assert "It lists the deeper imports that are meant to be usable from user code today." in text
    assert "`fuggers_py.curves.calibrators` | `CalibrationSpec`" in text
    assert "`fuggers_py.curves.kernels` | `KernelSpec`" in text
    assert "`fuggers_py.curves.conversion` | `ValueConverter`" in text
    assert "## Work In Progress" in text
    assert "`fuggers_py.curves.multicurve`" in text
    assert "`CurrencyPair` and `RateIndex`" in text
