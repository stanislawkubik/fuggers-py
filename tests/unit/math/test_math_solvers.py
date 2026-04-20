from __future__ import annotations

import math

import pytest

from fuggers_py._math import (
    BisectionSolver,
    BrentSolver,
    HybridSolver,
    MathResult,
    NewtonSolver,
    SecantSolver,
    Solver,
)
from fuggers_py._math.errors import ConvergenceFailed, InvalidBracket
from fuggers_py._math.solvers import (
    SolverConfig,
    bisection,
    brent,
    hybrid,
    hybrid_numerical,
    newton_raphson,
    newton_raphson_numerical,
    secant,
)


def _f(x: float) -> float:
    return x * x - 2.0


def _df(x: float) -> float:
    return 2.0 * x


@pytest.mark.parametrize(
    "solver",
    [
        lambda: bisection(_f, 1.0, 2.0),
        lambda: brent(_f, 1.0, 2.0),
        lambda: secant(_f, 1.0, 2.0),
        lambda: newton_raphson(_f, _df, 1.0),
        lambda: newton_raphson_numerical(_f, 1.0),
        lambda: hybrid(_f, _df, 1.0, 2.0, 1.5),
        lambda: hybrid_numerical(_f, 1.0, 2.0, 1.5),
    ],
)
def test_solvers_find_sqrt2(solver) -> None:
    res = solver()
    assert res.converged is True
    assert res.residual <= 1e-8
    assert res.root == pytest.approx(math.sqrt(2.0), rel=0, abs=1e-8)


def test_invalid_bracket_raises() -> None:
    with pytest.raises(InvalidBracket):
        _ = bisection(_f, 2.0, 3.0)
    with pytest.raises(InvalidBracket):
        _ = brent(_f, 2.0, 3.0)
    with pytest.raises(InvalidBracket):
        _ = hybrid(_f, _df, 2.0, 3.0, 2.5)


def test_convergence_failed_raises() -> None:
    config = SolverConfig(max_iterations=1, tolerance=1e-14)
    with pytest.raises(ConvergenceFailed):
        _ = bisection(_f, 1.0, 2.0, config=config)
    with pytest.raises(ConvergenceFailed):
        _ = brent(_f, 1.0, 2.0, config=config)
    with pytest.raises(ConvergenceFailed):
        _ = newton_raphson(_f, _df, 1.0, config=config)


@pytest.mark.parametrize(
    ("solver", "args"),
    [
        (BisectionSolver(config=SolverConfig(tolerance=1e-12, max_iterations=200)), (1.0, 2.0)),
        (BrentSolver(config=SolverConfig(tolerance=1e-12, max_iterations=200)), (1.0, 2.0)),
        (SecantSolver(config=SolverConfig(tolerance=1e-12, max_iterations=200)), (1.0, 2.0)),
        (NewtonSolver(config=SolverConfig(tolerance=1e-12, max_iterations=200), df=_df), (1.0,)),
        (HybridSolver(config=SolverConfig(tolerance=1e-12, max_iterations=200), df=_df), (1.0, 2.0, 1.5)),
    ],
)
def test_solver_instances_return_math_result(solver, args) -> None:
    assert isinstance(solver, Solver)

    result = solver.find_root(_f, *args)

    assert isinstance(result, MathResult)
    assert result.converged is True
    assert result.root == pytest.approx(math.sqrt(2.0), rel=0, abs=1e-10)
