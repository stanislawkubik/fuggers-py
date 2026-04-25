from __future__ import annotations

import ast
import inspect
from pathlib import Path

from fuggers_py import Date
import fuggers_py.vol_surfaces as vol_surfaces
from fuggers_py.vol_surfaces import (
    InMemoryVolatilitySource,
    VolPoint,
    VolQuoteType,
    VolSurfaceSourceType,
    VolSurfaceType,
    VolatilitySource,
    VolatilitySurface,
)


def test_vol_surfaces_root_exports_the_current_public_surface() -> None:
    assert vol_surfaces.__all__ == [
        "InMemoryVolatilitySource",
        "VolPoint",
        "VolQuoteType",
        "VolSurfaceSourceType",
        "VolSurfaceType",
        "VolatilitySource",
        "VolatilitySurface",
    ]


def test_vol_surfaces_root_is_a_small_direct_import_surface() -> None:
    vol_surfaces_init = Path(vol_surfaces.__file__)
    tree = ast.parse(vol_surfaces_init.read_text(encoding="utf-8"))

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


def test_vol_surface_exports_resolve_under_vol_surfaces() -> None:
    root = Path(vol_surfaces.__file__).resolve().parent
    for name in vol_surfaces.__all__:
        source = inspect.getsourcefile(getattr(vol_surfaces, name))
        assert source is not None
        assert Path(source).resolve().is_relative_to(root)


def test_vol_surface_records_and_sources_are_usable_from_root_exports() -> None:
    point = VolPoint(
        expiry="2027-06",
        tenor="2032-06",
        volatility="0.255",
        strike="0.03",
        quote_type=VolQuoteType.NORMAL,
    )
    surface = VolatilitySurface(
        surface_id="usd-swaption-grid",
        surface_type=VolSurfaceType.SWAPTION,
        as_of=Date.from_ymd(2026, 4, 16),
        points=(point,),
        source_type=VolSurfaceSourceType.MODEL,
    )
    source = InMemoryVolatilitySource([surface])

    assert isinstance(source, VolatilitySource)
    assert source.get_volatility_surface("usd-swaption-grid") is surface
    assert surface.points == (point,)
    assert surface.surface_type is VolSurfaceType.SWAPTION
    assert surface.source_type is VolSurfaceSourceType.MODEL
    assert point.quote_type is VolQuoteType.NORMAL
