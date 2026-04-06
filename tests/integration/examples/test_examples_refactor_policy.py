from __future__ import annotations

from tests.helpers._paths import REPO_ROOT


ROOT = REPO_ROOT
EXAMPLES = REPO_ROOT / "examples"

EXPECTED_ROOT_CONTENTS = {
    "01_cash_bond_and_curve_workflow.ipynb",
    "02_financed_tips_multi_curve_workflow.ipynb",
    "03_credit_basis_cross_market_and_optionality.ipynb",
    "04_portfolio_etf_and_engine_pipeline.ipynb",
    "05_fitted_nominal_real_breakeven_minimal.ipynb",
    "README.md",
    "synthetic_data",
}

BANNED_PATTERNS = (
    "fuggers_py.traits",
    "fuggers_py.ext",
    "tests.",
    "sys.path.insert",
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
