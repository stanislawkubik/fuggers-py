from __future__ import annotations

import os

import pytest

from tests.helpers._paths import REPO_ROOT


ROOT = REPO_ROOT
EXAMPLES = REPO_ROOT / "examples"
SYNTHETIC_DATA = EXAMPLES / "synthetic_data"

EXPECTED_NOTEBOOKS = {
    "01_public_curves_and_surfaces.ipynb",
    "05_fitted_nominal_real_breakeven_minimal.ipynb",
}

EXPECTED_SYNTHETIC_PATHS = {
    "bonds/call_schedule.csv",
    "bonds/cash_bond_market_levels.csv",
    "bonds/instruments.csv",
    "bonds/sinking_schedule.csv",
    "credit/cds_families.csv",
    "credit/cds_par_spreads.csv",
    "curves/benchmarks.csv",
    "curves/cash_breakeven_markers.csv",
    "curves/inflation_swap_curve.csv",
    "curves/nominal_government_curve.csv",
    "curves/ois_discount_curve.csv",
    "curves/real_rate_curve.csv",
    "curves/repo_funding_curve.csv",
    "fx/cross_currency_basis.csv",
    "fx/cross_currency_basis_instruments.csv",
    "inflation/realized_cpi.csv",
    "market_quotes.csv",
    "portfolio/positions.csv",
    "positions.csv",
    "realized_cpi.csv",
    "rates/rates_future_chain.csv",
    "rates/rates_futures.csv",
    "rates/rates_futures_basket.csv",
    "rates/rates_option_smile.csv",
    "rates/rates_options.csv",
    "reference_instruments.csv",
}


def test_examples_tree_matches_catalog() -> None:
    notebook_names = {path.name for path in EXAMPLES.glob("*.ipynb")}
    synthetic_paths = {
        path.relative_to(SYNTHETIC_DATA).as_posix()
        for path in SYNTHETIC_DATA.rglob("*")
        if path.is_file()
    }

    assert notebook_names == EXPECTED_NOTEBOOKS
    assert synthetic_paths == EXPECTED_SYNTHETIC_PATHS


@pytest.mark.parametrize("notebook_name", sorted(EXPECTED_NOTEBOOKS))
def test_example_notebook_executes(notebook_name: str) -> None:
    nbformat = pytest.importorskip("nbformat")
    nbclient = pytest.importorskip("nbclient")
    pytest.importorskip("ipykernel")

    notebook_path = EXAMPLES / notebook_name
    notebook = nbformat.read(notebook_path, as_version=4)
    previous_pythonpath = os.environ.get("PYTHONPATH")
    repo_pythonpath = str(ROOT / "src")
    os.environ["PYTHONPATH"] = (
        repo_pythonpath
        if not previous_pythonpath
        else f"{repo_pythonpath}{os.pathsep}{previous_pythonpath}"
    )
    client = nbclient.NotebookClient(
        notebook,
        timeout=300,
        kernel_name="python3",
        resources={"metadata": {"path": str(EXAMPLES)}},
    )

    try:
        client.execute()
    except PermissionError as exc:
        pytest.skip(f"Notebook execution requires local kernel ports in this environment: {exc}")
    finally:
        if previous_pythonpath is None:
            os.environ.pop("PYTHONPATH", None)
        else:
            os.environ["PYTHONPATH"] = previous_pythonpath
