from __future__ import annotations

from tests.helpers._paths import REPO_ROOT


ROOT = REPO_ROOT
EXAMPLES = REPO_ROOT / "examples"

EXPECTED_ROOT_CONTENTS = {
    "01_treasury_curve_fit.ipynb",
    "README.md",
}

BANNED_PATTERNS = (
    "fuggers_py._market.curves",
    "fuggers_py._market.vol_surfaces",
    "fuggers_py._market.quotes",
    "fuggers_py._products.",
    "fuggers_py._pricers.",
    "fuggers_py._measures.",
    "fuggers_py._reference.",
    "fuggers_py._calc.",
    "fuggers_py._storage.",
    "fuggers_py.curves.calibrators",
    "fuggers_py.curves.date_support",
    "fuggers_py.curves.kernels",
    "fuggers_py.fixings",
    "fuggers_py.derivatives",
    "from fuggers_py.core import",
    "fuggers_py.traits",
    "fuggers_py.ext",
    "tests.",
    "sys.path.insert",
)

BANNED_README_TEXT = (
    "01_public_curves_and_surfaces.ipynb",
    "02_treasury_curve_fit.ipynb",
    "05_fitted_nominal_real_breakeven_minimal.ipynb",
    "synthetic_data",
    "key_rate_bumped_curve",
    "parallel_bumped_curve",
    "fuggers_py.curves.calibrators",
    "fuggers_py.curves.date_support",
    "fuggers_py.curves.kernels",
)

LEGACY_DIRECTORIES = (
    "01_foundations",
    "02_curves",
    "03_bonds",
    "04_analytics",
    "05_portfolio",
    "06_data_io",
    "07_engine",
)


def test_examples_root_contains_only_flat_catalog() -> None:
    root_contents = {path.name for path in EXAMPLES.iterdir()}
    assert root_contents == EXPECTED_ROOT_CONTENTS


def test_examples_do_not_include_python_sources() -> None:
    assert list(EXAMPLES.rglob("*.py")) == []


def test_examples_do_not_include_legacy_directories() -> None:
    for directory_name in LEGACY_DIRECTORIES:
        assert not (EXAMPLES / directory_name).exists()


def test_examples_package_marker_is_absent() -> None:
    assert not (EXAMPLES / "__init__.py").exists()


def test_notebooks_avoid_banned_patterns() -> None:
    for notebook_path in EXAMPLES.glob("*.ipynb"):
        source = notebook_path.read_text()
        for pattern in BANNED_PATTERNS:
            assert pattern not in source, f"{pattern!r} found in {notebook_path.name}"


def test_examples_readme_mentions_only_the_current_example() -> None:
    text = (EXAMPLES / "README.md").read_text(encoding="utf-8")

    assert "01_treasury_curve_fit.ipynb" in text
    for pattern in BANNED_README_TEXT:
        assert pattern not in text
