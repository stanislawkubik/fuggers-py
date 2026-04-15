from __future__ import annotations

from fuggers_py.market.state import AnalyticsCurves


def test_analytics_curves_support_extended_curve_roles() -> None:
    discount_curve = object()
    repo_curve = object()
    collateral_curve = object()
    fx_forward_curve = object()
    environment = object()
    sofr_projection = object()
    vol_surface = object()

    curves = AnalyticsCurves(
        discount_curve=discount_curve,
        repo_curve=repo_curve,
        collateral_curve=collateral_curve,
        fx_forward_curve=fx_forward_curve,
        multicurve_environment=environment,
        projection_curves={"SOFR": sofr_projection},
        vol_surface=vol_surface,
    )

    assert curves.get("discount") is discount_curve
    assert curves.get("repo") is repo_curve
    assert curves.get("repo_curve") is repo_curve
    assert curves.get("collateral_curve") is collateral_curve
    assert curves.get("fx_forward_curve") is fx_forward_curve
    assert curves.get("multicurve_environment") is environment
    assert curves.get("projection_curves") == {"SOFR": sofr_projection}
    assert curves.get("projection:SOFR") is sofr_projection
    assert curves.get("projection:sofr") is sofr_projection
    assert curves.get("vol_surface") is vol_surface
    assert curves.get("missing-role") is None
