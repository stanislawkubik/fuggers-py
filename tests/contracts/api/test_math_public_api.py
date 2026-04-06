from __future__ import annotations

import math

import pytest

from fuggers_py.math import (
    BisectionSolver,
    BrentSolver,
    HybridSolver,
    MathResult,
    NewtonSolver,
    RootFinder,
    SecantSolver,
    Solver,
    SolverConfig,
)


def _f(x: float) -> float:
    return x * x - 2.0


def _df(x: float) -> float:
    return 2.0 * x


def test_solver_classes_are_runtime_protocol_compatible() -> None:
    config = SolverConfig(tolerance=1e-12, max_iterations=200)
    solvers = [
        BisectionSolver(config=config),
        BrentSolver(config=config),
        SecantSolver(config=config),
        NewtonSolver(config=config, df=_df),
        HybridSolver(config=config, df=_df),
    ]

    for solver in solvers:
        assert isinstance(solver, RootFinder)
        assert isinstance(solver, Solver)


def test_solver_classes_construct_and_execute() -> None:
    config = SolverConfig(tolerance=1e-12, max_iterations=200)
    solver_cases = [
        (BisectionSolver(config=config), (1.0, 2.0)),
        (BrentSolver(config=config), (1.0, 2.0)),
        (SecantSolver(config=config), (1.0, 2.0)),
        (NewtonSolver(config=config, df=_df), (1.0,)),
        (NewtonSolver(config=config), (1.0,)),
        (HybridSolver(config=config, df=_df), (1.0, 2.0, 1.5)),
        (HybridSolver(config=config), (1.0, 2.0, 1.5)),
    ]

    for solver, args in solver_cases:
        result = solver.find_root(_f, *args)
        assert isinstance(result, MathResult)
        assert result.converged is True
        assert result.root == pytest.approx(math.sqrt(2.0), rel=0, abs=1e-10)
