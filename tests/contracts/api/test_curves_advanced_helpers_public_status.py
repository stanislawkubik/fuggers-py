from __future__ import annotations

import ast
import json
from pathlib import Path

from fuggers_py import Compounding, Currency, Tenor
import fuggers_py.curves as curves
import fuggers_py.curves.calibrators as calibrators
import fuggers_py.curves.conversion as conversion
import fuggers_py.curves.date_support as date_support
import fuggers_py.curves.kernels as kernels
import fuggers_py.curves.movements as movements
import fuggers_py.curves.multicurve as multicurve
from fuggers_py.curves.calibrators import CalibrationSpec
from fuggers_py.curves.conversion import ValueConverter
from fuggers_py.curves.kernels import KernelSpec
from fuggers_py.curves.kernels.nodes import (
    LinearZeroKernel,
    LogLinearDiscountKernel,
    MonotoneConvexKernel,
    PiecewiseConstantZeroKernel,
    PiecewiseFlatForwardKernel,
)
from fuggers_py.curves.kernels.parametric import NelsonSiegelKernel, SvenssonKernel
from fuggers_py.curves.kernels.spline import CubicSplineKernel, ExponentialSplineKernel
from fuggers_py.curves.multicurve import CurrencyPair, RateIndex
from tests.helpers._paths import REPO_ROOT


SUBMODULE_ONLY_HELPERS = {
    "CalibrationSpec",
    "CubicSplineKernel",
    "CurrencyPair",
    "CurveCalibrator",
    "CurveKernel",
    "ExponentialSplineKernel",
    "KernelSpec",
    "LinearZeroKernel",
    "LogLinearDiscountKernel",
    "MonotoneConvexKernel",
    "NelsonSiegelKernel",
    "PiecewiseConstantZeroKernel",
    "PiecewiseFlatForwardKernel",
    "RateIndex",
    "SvenssonKernel",
    "ValueConverter",
    "curve_reference_date",
    "discount_factor_at_date",
    "forward_rate_between_dates",
    "tenor_from_curve_date",
    "year_fraction_from_curve",
    "zero_rate_at_date",
}


REMOVED_PUBLIC_NAMES = {
    "BondFitTarget",
    "CalibrationMode",
    "CalibrationObjective",
    "CurveKernelKind",
    "CurveType",
    "ExtrapolationPolicy",
    "GlobalFitOptimizerKind",
    "GlobalFitPoint",
    "GlobalFitReport",
    "key_rate_bumped_curve",
    "parallel_bumped_curve",
    "RateSpace",
    "RelativeRateCurve",
}


def _example_and_api_contract_sources() -> list[tuple[Path, str]]:
    sources: list[tuple[Path, str]] = []

    for path in sorted((REPO_ROOT / "tests" / "contracts" / "api").glob("*.py")):
        sources.append((path, path.read_text(encoding="utf-8")))

    for path in sorted((REPO_ROOT / "examples").glob("*.py")):
        sources.append((path, path.read_text(encoding="utf-8")))

    for path in sorted((REPO_ROOT / "examples").glob("*.ipynb")):
        notebook = json.loads(path.read_text(encoding="utf-8"))
        for cell in notebook.get("cells", []):
            if cell.get("cell_type") != "code":
                continue
            raw_source = cell.get("source", [])
            source = "".join(raw_source) if isinstance(raw_source, list) else str(raw_source)
            sources.append((path, source))

    return sources


def test_advanced_curve_helpers_are_not_curves_root_exports() -> None:
    for name in SUBMODULE_ONLY_HELPERS | REMOVED_PUBLIC_NAMES:
        assert name not in curves.__all__
        assert not hasattr(curves, name)


def test_examples_and_api_contracts_do_not_import_advanced_helpers_from_curves_root() -> None:
    offenders: list[str] = []
    banned_from_root = SUBMODULE_ONLY_HELPERS | REMOVED_PUBLIC_NAMES

    for path, source in _example_and_api_contract_sources():
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module != "fuggers_py.curves":
                continue
            imported_names = {alias.name for alias in node.names}
            banned_names = sorted(banned_from_root & imported_names)
            if "*" in imported_names:
                banned_names.append("*")
            if banned_names:
                location = f"{path.relative_to(REPO_ROOT)}:{node.lineno}"
                offenders.append(f"{location} imports {', '.join(banned_names)} from fuggers_py.curves")

    assert offenders == []


def test_conversion_helper_is_public_from_conversion_submodule_only() -> None:
    assert conversion.__all__ == ["ValueConverter"]
    assert ValueConverter is conversion.ValueConverter
    assert ValueConverter.convert_compounding(
        0.031,
        Compounding.CONTINUOUS,
        Compounding.CONTINUOUS,
    ) == 0.031


def test_date_support_exports_only_date_bridge_helpers() -> None:
    assert date_support.__all__ == [
        "curve_reference_date",
        "discount_factor_at_date",
        "forward_rate_between_dates",
        "tenor_from_curve_date",
        "year_fraction_from_curve",
        "zero_rate_at_date",
    ]


def test_curve_movement_constant_is_public_from_root_and_movements_module() -> None:
    assert movements.__all__ == ["STANDARD_KEY_RATE_TENORS"]
    assert curves.STANDARD_KEY_RATE_TENORS is movements.STANDARD_KEY_RATE_TENORS
    assert not hasattr(curves, "key_rate_bumped_curve")
    assert not hasattr(curves, "parallel_bumped_curve")


def test_advanced_fit_specs_are_public_from_submodules_only() -> None:
    assert kernels.__all__ == ["KernelSpec"]
    assert calibrators.__all__ == ["CalibrationSpec"]
    assert KernelSpec is kernels.KernelSpec
    assert CalibrationSpec is calibrators.CalibrationSpec


def test_concrete_kernels_are_importable_from_their_implementation_modules_only() -> None:
    concrete_kernels = [
        LinearZeroKernel,
        LogLinearDiscountKernel,
        MonotoneConvexKernel,
        PiecewiseConstantZeroKernel,
        PiecewiseFlatForwardKernel,
        NelsonSiegelKernel,
        SvenssonKernel,
        CubicSplineKernel,
        ExponentialSplineKernel,
    ]

    for kernel_type in concrete_kernels:
        assert kernel_type.__module__.startswith("fuggers_py.curves.kernels.")
        assert not hasattr(kernels, kernel_type.__name__)
        assert not hasattr(curves, kernel_type.__name__)


def test_multicurve_identifiers_are_public_from_multicurve_submodule_only() -> None:
    assert multicurve.__all__ == ["CurrencyPair", "RateIndex"]
    assert CurrencyPair is multicurve.CurrencyPair
    assert RateIndex is multicurve.RateIndex

    pair = CurrencyPair(base=Currency.USD, quote=Currency.EUR)
    index = RateIndex.new("sofr", Tenor.parse("3M"), Currency.USD)

    assert pair.code() == "USD/EUR"
    assert pair.inverse().code() == "EUR/USD"
    assert index.key() == "USD-SOFR-3M"
