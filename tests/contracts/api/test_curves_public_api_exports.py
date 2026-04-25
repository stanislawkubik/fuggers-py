from __future__ import annotations

import ast
import inspect
from pathlib import Path

from fuggers_py import Date
import fuggers_py.curves as curves
from fuggers_py.curves import (
    CurveSpec,
    DiscountingCurve,
    RatesTermStructure,
    YieldCurve,
)


REMOVED_CURVE_BUCKET = "_curves" "_impl"


def test_curves_root_reexports_basic_curve_types() -> None:
    assert CurveSpec is curves.CurveSpec
    assert RatesTermStructure is curves.RatesTermStructure
    assert DiscountingCurve is curves.DiscountingCurve
    assert YieldCurve is curves.YieldCurve
    assert issubclass(DiscountingCurve, RatesTermStructure)
    assert issubclass(YieldCurve, DiscountingCurve)
    assert CurveSpec.__module__ == "fuggers_py.curves.spec"
    assert RatesTermStructure.__module__ == "fuggers_py.curves.base"
    assert DiscountingCurve.__module__ == "fuggers_py.curves.base"
    assert YieldCurve.__module__ == "fuggers_py.curves.base"


def test_curves_root_is_a_small_direct_import_surface() -> None:
    curves_init = Path(curves.__file__)
    tree = ast.parse(curves_init.read_text(encoding="utf-8"))

    assert "__getattr__" not in {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert "__getattr__" not in {node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in {"import_module", "__import__"}
            elif isinstance(node.func, ast.Attribute):
                assert not (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "importlib"
                    and node.func.attr == "import_module"
                )


def test_curves_root_imports_only_local_curve_files() -> None:
    curves_init = Path(curves.__file__)
    tree = ast.parse(curves_init.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                continue
            assert node.level == 1
            assert node.module is not None


def test_curves_exports_resolve_under_curves() -> None:
    root = Path(curves.__file__).resolve().parent
    source_less_constants = {"STANDARD_KEY_RATE_TENORS"}
    for name in curves.__all__:
        try:
            source = inspect.getsourcefile(getattr(curves, name))
        except TypeError:
            source = None
        if source is None:
            assert name in source_less_constants
            continue
        assert source is not None
        assert Path(source).resolve().is_relative_to(root)


def test_date_support_stays_off_removed_curve_bucket() -> None:
    date_support = Path(curves.__file__).resolve().parent / "date_support.py"
    tree = ast.parse(date_support.read_text(encoding="utf-8"))

    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert all(REMOVED_CURVE_BUCKET not in module for module in imported_modules)


def test_curves_root_does_not_reintroduce_removed_symbols() -> None:
    legacy_names = [
        "BondFitTarget",
        "CalibrationMode",
        "CalibrationObjective",
        "CalibrationSpec",
        "Compounding",
        "CubicSpline",
        "CurveKernel",
        "CurveKernelKind",
        "CurveError",
        "CurveType",
        "DiscountCurveBuilder",
        "ExtrapolationPolicy",
        "GlobalFitOptimizerKind",
        "GlobalFitPoint",
        "GlobalFitReport",
        "Interpolator",
        "JumpDiffusionCurve",
        "KernelSpec",
        "LinearInterpolator",
        "LogLinearInterpolator",
        "MonotoneConvex",
        "NelsonSiegel",
        "RateSpace",
        "RelativeRateCurve",
        "ShadowRateCurve",
        "Svensson",
        "TermStructure",
        "Tenor",
        "ZeroCurveBuilder",
    ]

    for name in legacy_names:
        assert not hasattr(curves, name)


def test_curve_spec_can_be_built_from_the_first_layer_exports() -> None:
    reference_date = Date.from_ymd(2024, 1, 1)
    spec = CurveSpec(
        name="USD OIS",
        reference_date=reference_date,
        day_count="act/365f",
        currency="usd",
        type="overnight_discount",
        extrapolation_policy="error",
    )

    assert spec.name == "USD OIS"
    assert spec.reference_date == reference_date
    assert spec.day_count == "ACT/365F"
    assert spec.currency.code() == "USD"
    assert spec.type == "overnight_discount"
    assert spec.extrapolation_policy == "error"
    assert YieldCurve.__name__ == "YieldCurve"
