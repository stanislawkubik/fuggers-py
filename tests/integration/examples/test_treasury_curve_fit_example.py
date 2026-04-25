from __future__ import annotations

import json
from typing import Any, cast

import pytest

from tests.helpers._paths import REPO_ROOT


NOTEBOOK_PATH = REPO_ROOT / "examples" / "01_treasury_curve_fit.ipynb"


def _source() -> str:
    notebook = cast(dict[str, Any], json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8")))
    cells = cast(list[dict[str, Any]], notebook["cells"])
    return "\n".join("".join(cast(list[str], cell["source"])) for cell in cells)


def _executed_fit_namespace() -> dict[str, Any]:
    notebook = cast(dict[str, Any], json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8")))
    cells = cast(list[dict[str, Any]], notebook["cells"])
    setup_sources: list[str] = []
    for cell in cells:
        if cell["cell_type"] != "code":
            continue
        source = "".join(cast(list[str], cell["source"]))
        if source.startswith("fit_points = pd.DataFrame"):
            break
        setup_sources.append(source)

    namespace: dict[str, Any] = {}
    exec("\n".join(setup_sources), namespace)
    return namespace


def test_treasury_curve_fit_notebook_is_the_only_current_example() -> None:
    assert NOTEBOOK_PATH.exists()
    assert {path.name for path in (REPO_ROOT / "examples").glob("*.ipynb")} == {
        "01_treasury_curve_fit.ipynb"
    }


def test_treasury_curve_fit_notebook_uses_default_fit_before_advanced_comparison() -> None:
    source = _source()
    default_index = source.index("default_curve = YieldCurve.fit(quotes, spec=curve_spec)")
    no_regressor_index = source.index("spline_no_regressors = YieldCurve.fit(")
    advanced_index = source.index("spline_curve = YieldCurve.fit(")

    assert default_index < no_regressor_index < advanced_index
    assert 'kernel="cubic_spline"' in source[advanced_index:]
    assert 'method="global_fit"' in source[advanced_index:]
    assert 'regressors=("liquidity", "specialness")' in source[advanced_index:]
    assert "one ignores regressors, and one uses liquidity and specialness" in source


def test_treasury_curve_fit_notebook_models_price_noise_and_regressor_effects() -> None:
    source = _source()

    assert "TRUE_LIQUIDITY_COEF = 0.22" in source
    assert "TRUE_SPECIALNESS_COEF = 0.14" in source
    assert "regressor_effect = TRUE_LIQUIDITY_COEF * liquidity + TRUE_SPECIALNESS_COEF * specialness" in source
    assert "clean_price = curve_clean + Decimal(str(regressor_effect + noise))" in source
    assert '"true_price_coefficient": (TRUE_LIQUIDITY_COEF, TRUE_SPECIALNESS_COEF)' in source
    assert '"fitted_price_coefficient": report.regressor_coefficients' in source
    assert 'regressor_fit["coefficient_error"]' in source


def test_treasury_curve_fit_notebook_checks_curve_recovery() -> None:
    source = _source()

    assert "clean_knots = (1.0, 2.0, 4.0, 7.0, 12.0, 20.0, 31.0)" in source
    assert "curve_recovery = pd.DataFrame" in source
    assert "spline_no_regressors.zero_rate_at" in source
    assert '"knots": (0.5' not in source
    assert "front_grid" not in source
    assert "front_error_summary" not in source
    assert "Front-End Check" not in source


def test_treasury_curve_fit_notebook_uses_non_popup_plot_backend() -> None:
    source = _source()

    assert 'ipython.run_line_magic("matplotlib", "inline")' in source
    assert 'matplotlib.use("Agg")' in source
    assert "def show_figure(fig):" in source
    assert "display(fig)" in source
    assert "plt.close(fig)" in source
    assert "plt.show()" not in source
    assert source.index("import matplotlib\n") < source.index("import matplotlib.pyplot as plt")


def test_treasury_curve_fit_notebook_recovers_regressor_effects() -> None:
    np = pytest.importorskip("numpy")
    namespace = _executed_fit_namespace()

    report = namespace["report"]
    no_regressor_report = namespace["spline_no_regressors_report"]
    curve_recovery = namespace["curve_recovery"].set_index("fit")
    fitted_coefficients = np.asarray(report.regressor_coefficients, dtype=float)
    true_coefficients = np.asarray(
        [namespace["TRUE_LIQUIDITY_COEF"], namespace["TRUE_SPECIALNESS_COEF"]],
        dtype=float,
    )

    assert report.max_abs_residual < no_regressor_report.max_abs_residual
    assert (
        curve_recovery.loc["spline + regressors", "mean_abs_zero_error_bp"]
        < curve_recovery.loc["spline, no regressors", "mean_abs_zero_error_bp"]
    )
    assert np.max(np.abs(fitted_coefficients - true_coefficients)) < 0.075


def test_treasury_curve_fit_notebook_covers_curve_queries_and_moves() -> None:
    source = _source()

    assert "curve.zero_rate_at(" in source
    assert "curve.discount_factor_at(" in source
    assert "curve.forward_rate_between(" in source
    assert "curve.shifted(shift=0.00025)" in source
    assert "curve.bumped(" in source
    assert "STANDARD_KEY_RATE_TENORS" in source
    assert "BondPricer()" in source


def test_treasury_curve_fit_notebook_is_self_contained_and_first_layer_only() -> None:
    source = _source()
    banned_patterns = (
        "read_csv",
        ".csv",
        "synthetic_data",
        "requests.",
        "http://",
        "https://",
        "fuggers_py.curves.calibrators",
        "fuggers_py.curves.date_support",
        "fuggers_py.curves.kernels",
        "key_rate_bumped_curve",
        "parallel_bumped_curve",
    )

    assert "MATURITIES = (1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20, 25, 30)" in source
    assert 'instrument_id=f"UST{years}Y"' in source
    for pattern in banned_patterns:
        assert pattern not in source
