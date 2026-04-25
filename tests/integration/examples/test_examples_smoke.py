from __future__ import annotations

import os

import pytest

from tests.helpers._paths import REPO_ROOT


ROOT = REPO_ROOT
EXAMPLES = REPO_ROOT / "examples"

EXPECTED_NOTEBOOKS = {
    "01_treasury_curve_fit.ipynb",
}


def test_examples_tree_matches_catalog() -> None:
    notebook_names = {path.name for path in EXAMPLES.glob("*.ipynb")}
    directory_names = {path.name for path in EXAMPLES.iterdir() if path.is_dir()}

    assert notebook_names == EXPECTED_NOTEBOOKS
    assert directory_names == set()


@pytest.mark.parametrize("notebook_name", sorted(EXPECTED_NOTEBOOKS))
def test_example_notebook_executes(notebook_name: str) -> None:
    nbformat = pytest.importorskip("nbformat")
    nbclient = pytest.importorskip("nbclient")
    pytest.importorskip("ipykernel")

    notebook_path = EXAMPLES / notebook_name
    notebook = nbformat.read(notebook_path, as_version=4)
    previous_pythonpath = os.environ.get("PYTHONPATH")
    previous_mplbackend = os.environ.get("MPLBACKEND")
    repo_pythonpath = str(ROOT / "src")
    os.environ["PYTHONPATH"] = (
        repo_pythonpath
        if not previous_pythonpath
        else f"{repo_pythonpath}{os.pathsep}{previous_pythonpath}"
    )
    os.environ["MPLBACKEND"] = "Agg"
    client = nbclient.NotebookClient(
        notebook,
        timeout=300,
        kernel_name="python3",
        resources={"metadata": {"path": str(EXAMPLES)}},
    )

    try:
        executed = client.execute()
        plot_call_count = sum(
            sum(
                line.strip() == "show_figure(fig)"
                for line in str(cell.get("source", "")).splitlines()
            )
            for cell in notebook.cells
            if cell.get("cell_type") == "code"
        )
        inline_plot_count = sum(
            1
            for cell in executed.cells
            for output in cell.get("outputs", [])
            if "image/png" in output.get("data", {})
        )
        assert inline_plot_count == plot_call_count
    except PermissionError as exc:
        pytest.skip(f"Notebook execution requires local kernel ports in this environment: {exc}")
    finally:
        if previous_pythonpath is None:
            os.environ.pop("PYTHONPATH", None)
        else:
            os.environ["PYTHONPATH"] = previous_pythonpath
        if previous_mplbackend is None:
            os.environ.pop("MPLBACKEND", None)
        else:
            os.environ["MPLBACKEND"] = previous_mplbackend
