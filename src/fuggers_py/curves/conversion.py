"""Value conversion utilities for curve primitives.

The helpers in this module convert between curve node conventions using raw
decimal rates, probabilities, and discount factors.  All tenor arguments are
year fractions unless a calling convention explicitly provides a date.
"""

from __future__ import annotations

import math

from fuggers_py._core.types import Compounding

from .errors import InvalidCurveInput


def _require_positive(value: float, *, name: str) -> float:
    """Return ``value`` as a strictly positive, finite float."""

    numeric = float(value)
    if numeric <= 0.0 or not math.isfinite(numeric):
        raise InvalidCurveInput(f"{name} must be positive and finite.")
    return numeric


def _require_probability(value: float, *, name: str) -> float:
    """Return ``value`` as a probability in the closed unit interval."""

    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0.0 or numeric > 1.0:
        raise InvalidCurveInput(f"{name} must lie in [0, 1].")
    return numeric


class ValueConverter:
    """Convert between curve node conventions.

    The conversions operate on raw decimal quantities.  Percent presentation
    is intentionally left to the caller.
    """

    @staticmethod
    def df_to_zero(discount_factor: float, t: float, compounding: Compounding) -> float:
        """Convert a discount factor to a zero rate.

        Parameters
        ----------
        discount_factor
            Unitless discount factor at tenor ``t``.
        t
            Tenor in years.
        compounding
            Target compounding convention for the returned zero rate.
        """

        df = float(discount_factor)
        tau = float(t)
        if tau == 0.0:
            return 0.0
        if tau < 0.0:
            raise InvalidCurveInput("Tenor must be non-negative.")
        df = _require_positive(df, name="discount_factor")

        match compounding:
            case Compounding.CONTINUOUS:
                return float(-math.log(df) / tau)
            case Compounding.SIMPLE:
                return float((1.0 / df - 1.0) / tau)
            case Compounding.ANNUAL:
                return float(df ** (-1.0 / tau) - 1.0)
            case Compounding.SEMI_ANNUAL:
                return float(2.0 * (df ** (-1.0 / (2.0 * tau)) - 1.0))
            case Compounding.QUARTERLY:
                return float(4.0 * (df ** (-1.0 / (4.0 * tau)) - 1.0))
            case Compounding.MONTHLY:
                return float(12.0 * (df ** (-1.0 / (12.0 * tau)) - 1.0))
            case Compounding.DAILY:
                return float(365.0 * (df ** (-1.0 / (365.0 * tau)) - 1.0))
            case _:
                raise InvalidCurveInput(f"Unsupported compounding convention: {compounding!r}.")

    @staticmethod
    def zero_to_df(zero_rate: float, t: float, compounding: Compounding) -> float:
        """Convert a zero rate to a discount factor.

        Parameters
        ----------
        zero_rate
            Raw decimal zero rate.
        t
            Tenor in years.
        compounding
            Compounding convention used by ``zero_rate``.
        """

        r = float(zero_rate)
        tau = float(t)
        if tau == 0.0:
            return 1.0
        if tau < 0.0:
            raise InvalidCurveInput("Tenor must be non-negative.")

        match compounding:
            case Compounding.CONTINUOUS:
                return float(math.exp(-r * tau))
            case Compounding.SIMPLE:
                if 1.0 + r * tau <= 0.0:
                    raise InvalidCurveInput("Simple-compounded zero rate implies a non-positive discount factor.")
                return float(1.0 / (1.0 + r * tau))
            case Compounding.ANNUAL:
                if 1.0 + r <= 0.0:
                    raise InvalidCurveInput("Annual-compounded zero rate implies a non-positive discount factor.")
                return float((1.0 + r) ** (-tau))
            case Compounding.SEMI_ANNUAL:
                if 1.0 + r / 2.0 <= 0.0:
                    raise InvalidCurveInput("Semi-annual zero rate implies a non-positive discount factor.")
                return float((1.0 + r / 2.0) ** (-2.0 * tau))
            case Compounding.QUARTERLY:
                if 1.0 + r / 4.0 <= 0.0:
                    raise InvalidCurveInput("Quarterly zero rate implies a non-positive discount factor.")
                return float((1.0 + r / 4.0) ** (-4.0 * tau))
            case Compounding.MONTHLY:
                if 1.0 + r / 12.0 <= 0.0:
                    raise InvalidCurveInput("Monthly zero rate implies a non-positive discount factor.")
                return float((1.0 + r / 12.0) ** (-12.0 * tau))
            case Compounding.DAILY:
                if 1.0 + r / 365.0 <= 0.0:
                    raise InvalidCurveInput("Daily zero rate implies a non-positive discount factor.")
                return float((1.0 + r / 365.0) ** (-365.0 * tau))
            case _:
                raise InvalidCurveInput(f"Unsupported compounding convention: {compounding!r}.")

    @staticmethod
    def _to_continuous(rate: float, compounding: Compounding) -> float:
        """Convert a rate from the given compounding to continuous compounding."""

        r = float(rate)
        match compounding:
            case Compounding.CONTINUOUS:
                return r
            case Compounding.SIMPLE | Compounding.ANNUAL:
                if 1.0 + r <= 0.0:
                    raise InvalidCurveInput("Rate implies a non-positive one-year accumulation factor.")
                return float(math.log(1.0 + r))
            case Compounding.SEMI_ANNUAL:
                if 1.0 + r / 2.0 <= 0.0:
                    raise InvalidCurveInput("Rate implies a non-positive semi-annual accumulation factor.")
                return float(2.0 * math.log(1.0 + r / 2.0))
            case Compounding.QUARTERLY:
                if 1.0 + r / 4.0 <= 0.0:
                    raise InvalidCurveInput("Rate implies a non-positive quarterly accumulation factor.")
                return float(4.0 * math.log(1.0 + r / 4.0))
            case Compounding.MONTHLY:
                if 1.0 + r / 12.0 <= 0.0:
                    raise InvalidCurveInput("Rate implies a non-positive monthly accumulation factor.")
                return float(12.0 * math.log(1.0 + r / 12.0))
            case Compounding.DAILY:
                if 1.0 + r / 365.0 <= 0.0:
                    raise InvalidCurveInput("Rate implies a non-positive daily accumulation factor.")
                return float(365.0 * math.log(1.0 + r / 365.0))
            case _:
                raise InvalidCurveInput(f"Unsupported compounding convention: {compounding!r}.")

    @staticmethod
    def _from_continuous(continuous_rate: float, target_compounding: Compounding) -> float:
        """Convert a continuously compounded rate to ``target_compounding``."""

        rc = float(continuous_rate)
        match target_compounding:
            case Compounding.CONTINUOUS:
                return rc
            case Compounding.SIMPLE | Compounding.ANNUAL:
                return float(math.exp(rc) - 1.0)
            case Compounding.SEMI_ANNUAL:
                return float(2.0 * (math.exp(rc / 2.0) - 1.0))
            case Compounding.QUARTERLY:
                return float(4.0 * (math.exp(rc / 4.0) - 1.0))
            case Compounding.MONTHLY:
                return float(12.0 * (math.exp(rc / 12.0) - 1.0))
            case Compounding.DAILY:
                return float(365.0 * (math.exp(rc / 365.0) - 1.0))
            case _:
                raise InvalidCurveInput(f"Unsupported compounding convention: {target_compounding!r}.")

    @staticmethod
    def convert_compounding(rate: float, from_compounding: Compounding, to_compounding: Compounding) -> float:
        """Convert a raw decimal rate between compounding conventions."""

        if from_compounding == to_compounding:
            return float(rate)
        return ValueConverter._from_continuous(
            ValueConverter._to_continuous(rate, from_compounding),
            to_compounding,
        )

    @staticmethod
    def instantaneous_forward(zero_rate: float, d_zero_dt: float, t: float) -> float:
        """Return the instantaneous forward rate implied by a zero curve."""

        return float(zero_rate) + float(t) * float(d_zero_dt)

    @staticmethod
    def forward_rate_from_zeros(zero1: float, zero2: float, t1: float, t2: float) -> float:
        """Return the forward rate implied by two zero rates.

        The inputs are raw decimal zero rates observed at tenors ``t1`` and
        ``t2`` in years.
        """

        dt = float(t2) - float(t1)
        if abs(dt) < 1e-10:
            return float(zero2)
        return float((float(t2) * float(zero2) - float(t1) * float(zero1)) / dt)

    @staticmethod
    def forward_rate_from_dfs(
        df1: float,
        df2: float,
        t1: float,
        t2: float,
        compounding: Compounding,
    ) -> float:
        """Return the forward rate implied by two discount factors."""

        dt = float(t2) - float(t1)
        if dt <= 0.0:
            raise InvalidCurveInput("Forward-rate end tenor must be greater than start tenor.")
        df_start = _require_positive(df1, name="df1")
        df_end = _require_positive(df2, name="df2")

        ratio = df_start / df_end
        match compounding:
            case Compounding.CONTINUOUS:
                return float(math.log(ratio) / dt)
            case Compounding.SIMPLE:
                return float((ratio - 1.0) / dt)
            case _:
                forward_cont = float(math.log(ratio) / dt)
                return ValueConverter._from_continuous(forward_cont, compounding)

    @staticmethod
    def survival_to_hazard(survival_prob: float, d_survival_dt: float) -> float:
        """Convert a survival-probability slope to an instantaneous hazard."""

        sp = _require_probability(survival_prob, name="survival_prob")
        if sp == 0.0:
            raise InvalidCurveInput("survival_prob must be strictly positive for hazard conversion.")
        hazard = float(-float(d_survival_dt) / sp)
        if hazard < -1e-12:
            raise InvalidCurveInput("Survival probability slope implies a negative hazard rate.")
        return max(hazard, 0.0)

    @staticmethod
    def hazard_to_survival(hazard_rate: float, t: float) -> float:
        """Convert a flat hazard rate to a survival probability at tenor ``t``."""

        if float(t) < 0.0:
            raise InvalidCurveInput("Tenor must be non-negative.")
        if float(hazard_rate) < 0.0:
            raise InvalidCurveInput("hazard_rate must be non-negative.")
        return float(math.exp(-float(hazard_rate) * float(t)))

    @staticmethod
    def implied_hazard_rate(survival_prob: float, t: float) -> float:
        """Return the flat hazard rate implied by a survival probability."""

        tau = float(t)
        if tau == 0.0:
            return 0.0
        if tau < 0.0:
            raise InvalidCurveInput("Tenor must be non-negative.")
        sp = _require_probability(survival_prob, name="survival_prob")
        if sp == 0.0:
            raise InvalidCurveInput("survival_prob must be strictly positive for hazard conversion.")
        return float(-math.log(sp) / tau)

    @staticmethod
    def risky_discount_factor(df: float, survival_prob: float, recovery_rate: float) -> float:
        """Return the risky discount factor including fractional recovery.

        The result is the risk-free discount factor multiplied by the expected
        payoff weight ``survival_prob + (1 - survival_prob) * recovery_rate``.
        Recovery is a raw decimal fraction in ``[0, 1]``.
        """

        discount_factor = _require_positive(df, name="df")
        sp = _require_probability(survival_prob, name="survival_prob")
        rec = _require_probability(recovery_rate, name="recovery_rate")
        return discount_factor * float(sp + (1.0 - sp) * rec)


__all__ = ["ValueConverter"]
