from __future__ import annotations

import ast
from pathlib import Path

from fuggers_py import Date
import fuggers_py.curves as curves
from fuggers_py.curves import (
    CurveSpec,
    CurveType,
    DiscountingCurve,
    ExtrapolationPolicy,
    RateSpace,
    RatesTermStructure,
    RelativeRateCurve,
    YieldCurve,
)


def test_curves_root_reexports_basic_curve_types() -> None:
    assert CurveSpec is curves.CurveSpec
    assert CurveType is curves.CurveType
    assert ExtrapolationPolicy is curves.ExtrapolationPolicy
    assert RateSpace is curves.RateSpace
    assert RatesTermStructure is curves.RatesTermStructure
    assert DiscountingCurve is curves.DiscountingCurve
    assert RelativeRateCurve is curves.RelativeRateCurve
    assert YieldCurve is curves.YieldCurve
    assert issubclass(DiscountingCurve, RatesTermStructure)
    assert issubclass(YieldCurve, DiscountingCurve)
    assert issubclass(RelativeRateCurve, RatesTermStructure)
    assert CurveSpec.__module__ == "fuggers_py.curves.spec"
    assert CurveType.__module__ == "fuggers_py.curves.enums"
    assert ExtrapolationPolicy.__module__ == "fuggers_py.curves.enums"
    assert RateSpace.__module__ == "fuggers_py.curves.enums"
    assert RatesTermStructure.__module__ == "fuggers_py.curves.base"
    assert DiscountingCurve.__module__ == "fuggers_py.curves.base"
    assert RelativeRateCurve.__module__ == "fuggers_py.curves.base"
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


def test_curve_support_stays_off__curves_impl() -> None:
    curve_support = Path(curves.__file__).resolve().parent.parent / "_market" / "curve_support.py"
    tree = ast.parse(curve_support.read_text(encoding="utf-8"))

    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert "fuggers_py.curves" in imported_modules
    assert all(not module.startswith("fuggers_py._curves_impl") for module in imported_modules)


def test_curves_root_does_not_reintroduce_removed_symbols() -> None:
    legacy_names = [
        "Compounding",
        "CubicSpline",
        "CurveError",
        "DiscountCurveBuilder",
        "Interpolator",
        "JumpDiffusionCurve",
        "LinearInterpolator",
        "LogLinearInterpolator",
        "MonotoneConvex",
        "NelsonSiegel",
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
        type=CurveType.OVERNIGHT_DISCOUNT,
        extrapolation_policy=ExtrapolationPolicy.ERROR,
    )

    assert spec.name == "USD OIS"
    assert spec.reference_date == reference_date
    assert spec.day_count == "ACT/365F"
    assert spec.currency.code() == "USD"
    assert spec.type is CurveType.OVERNIGHT_DISCOUNT
    assert spec.extrapolation_policy is ExtrapolationPolicy.ERROR
    assert YieldCurve.__name__ == "YieldCurve"
    assert RateSpace.ZERO.name == "ZERO"
