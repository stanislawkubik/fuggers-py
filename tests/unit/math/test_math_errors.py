from __future__ import annotations

import pytest

from fuggers_py._math.errors import (
    ConvergenceFailed,
    DivisionByZero,
    DimensionMismatch,
    ExtrapolationNotAllowed,
    InsufficientData,
    InvalidBracket,
    InvalidInput,
    MathError,
    MathOverflow,
    MathUnderflow,
    SingularMatrix,
)


def test_error_payloads_and_str() -> None:
    err = ConvergenceFailed(iterations=5, residual=1e-3)
    assert err.iterations == 5
    assert err.residual == 1e-3
    assert "Convergence failed" in str(err)

    br = InvalidBracket(a=0.0, b=1.0, fa=1.0, fb=2.0)
    assert br.a == 0.0
    assert "Invalid bracket" in str(br)

    dz = DivisionByZero(value=0.0)
    assert "Division by zero" in str(dz)

    sm = SingularMatrix()
    assert "Singular matrix" in str(sm)

    dm = DimensionMismatch(rows1=2, cols1=2, rows2=3, cols2=1)
    assert "Dimension mismatch" in str(dm)

    ex = ExtrapolationNotAllowed(x=2.0, min=0.0, max=1.0)
    assert "Extrapolation not allowed" in str(ex)

    ins = InsufficientData(required=2, actual=1)
    assert "Insufficient data" in str(ins)

    inv = InvalidInput(reason="bad")
    assert "Invalid input" in str(inv)

    of = MathOverflow(operation="exp")
    assert "overflow" in str(of).lower()

    uf = MathUnderflow(operation="exp")
    assert "underflow" in str(uf).lower()


def test_error_constructor_helpers() -> None:
    err = MathError.convergence_failed(10, 0.25)
    assert isinstance(err, ConvergenceFailed)
    assert err.iterations == 10

    err2 = MathError.invalid_input("nope")
    assert isinstance(err2, InvalidInput)
    assert "nope" in str(err2)

    err3 = MathError.insufficient_data(3, 1)
    assert isinstance(err3, InsufficientData)
    assert err3.required == 3


def test_invalid_input_is_exception() -> None:
    with pytest.raises(MathError):
        raise InvalidInput(reason="x")

