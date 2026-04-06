"""Bond risk measures (`fuggers_py.pricers.bonds.risk.metrics`)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.reference.bonds.errors import InvalidBondSpec
from fuggers_py.products.bonds.traits import Bond
from fuggers_py.reference.bonds.types import CompoundingKind, YieldCalculationRules
from fuggers_py.core.types import Date, Yield

from ..pricer import BondPricer
from ..yield_engine import _prepare_cashflows


@dataclass(frozen=True, slots=True)
class _AnalyticalRiskComponents:
    """Intermediate analytical sensitivity components."""

    dirty_price: float
    modified_duration: float
    macaulay_duration: float
    convexity: float
    dv01: float


def _discount_factor_second_derivative(
    yield_rate: float,
    t: float,
    *,
    rules: YieldCalculationRules,
) -> float:
    compounding = rules.compounding
    y = float(yield_rate)
    tau = float(t)
    if tau == 0.0:
        return 0.0

    if compounding.kind in {CompoundingKind.PERIODIC, CompoundingKind.ACTUAL_PERIOD}:
        if compounding.frequency is None:
            raise InvalidBondSpec(reason="Periodic compounding requires a frequency.")
        frequency = float(compounding.frequency)
        base = 1.0 + y / frequency
        if base <= 0.0:
            raise InvalidBondSpec(reason="Yield is outside the valid periodic-compounding domain.")
        discount_factor = compounding.discount_factor(y, tau)
        return tau * (tau + 1.0 / frequency) * discount_factor / (base * base)

    if compounding.kind is CompoundingKind.CONTINUOUS:
        discount_factor = compounding.discount_factor(y, tau)
        return tau * tau * discount_factor

    if compounding.kind in {CompoundingKind.SIMPLE, CompoundingKind.DISCOUNT}:
        base = 1.0 + y * tau
        if base <= 0.0:
            raise InvalidBondSpec(reason="Yield is outside the valid simple-compounding domain.")
        return 2.0 * tau * tau / (base * base * base)

    raise InvalidBondSpec(reason=f"Unsupported compounding kind: {compounding.kind!r}.")


def _analytical_risk_components(
    instrument_or_cashflows,
    ytm: Yield,
    settlement_date: Date,
    *,
    rules: YieldCalculationRules | None = None,
) -> _AnalyticalRiskComponents:
    pricer = BondPricer()
    if rules is None:
        rules = instrument_or_cashflows.rules()
        projected_cashflows = instrument_or_cashflows.cash_flows()
    else:
        projected_cashflows = list(instrument_or_cashflows)
    yield_rate = float(pricer._yield_to_engine_rate(ytm, rules=rules))
    cashflows = _prepare_cashflows(
        projected_cashflows,
        settlement_date=settlement_date,
        rules=rules,
    )
    if not cashflows:
        return _AnalyticalRiskComponents(
            dirty_price=0.0,
            modified_duration=0.0,
            macaulay_duration=0.0,
            convexity=0.0,
            dv01=0.0,
        )

    dirty_price = 0.0
    first_derivative = 0.0
    second_derivative = 0.0
    macaulay_numerator = 0.0
    compounding = rules.compounding

    for cashflow in cashflows:
        discount_factor = compounding.discount_factor(yield_rate, cashflow.years)
        present_value = cashflow.amount * discount_factor
        dirty_price += present_value
        first_derivative += cashflow.amount * compounding.discount_factor_derivative(yield_rate, cashflow.years)
        second_derivative += cashflow.amount * _discount_factor_second_derivative(
            yield_rate,
            cashflow.years,
            rules=rules,
        )
        macaulay_numerator += cashflow.years * present_value

    if dirty_price == 0.0:
        return _AnalyticalRiskComponents(
            dirty_price=0.0,
            modified_duration=0.0,
            macaulay_duration=0.0,
            convexity=0.0,
            dv01=0.0,
        )

    modified_duration = -(first_derivative / dirty_price)
    macaulay_duration = macaulay_numerator / dirty_price
    convexity = second_derivative / dirty_price
    dv01 = -first_derivative * 1e-4

    return _AnalyticalRiskComponents(
        dirty_price=dirty_price,
        modified_duration=modified_duration,
        macaulay_duration=macaulay_duration,
        convexity=convexity,
        dv01=dv01,
    )


@dataclass(frozen=True, slots=True)
class RiskMetrics:
    """Duration, convexity, and signed DV01 measured off a bond yield.

    The measures are computed from the bond's dirty-price/yield relationship
    using the bond's configured compounding and settlement rules.
    """

    modified_duration: Decimal
    macaulay_duration: Decimal
    convexity: Decimal
    dv01: Decimal

    @property
    def duration(self) -> Decimal:
        """Alias for modified duration."""
        return self.modified_duration

    @property
    def pv01(self) -> Decimal:
        """Compatibility alias for DV01.

        The sign convention follows the library DV01 rule: the value is
        positive when bond value rises as yield falls by 1 basis point.
        """
        return self.dv01

    @classmethod
    def from_bond(
        cls,
        bond: Bond,
        ytm: Yield,
        settlement_date: Date,
        *,
        bump: float = 1e-4,
    ) -> "RiskMetrics":
        """Compute analytical and bumped risk measures for a bond.

        Modified duration is reported per unit yield. DV01 is the
        percent-of-par price change per 1 basis point move in yield, signed
        positive when bond value rises as yield falls by 1 bp. ``pv01`` is a
        compatibility alias of the same value.
        """
        return cls.from_projected_cashflows(
            bond.cash_flows(),
            ytm,
            settlement_date,
            rules=bond.rules(),
            bump=bump,
        )

    @classmethod
    def from_projected_cashflows(
        cls,
        cashflows,
        ytm: Yield,
        settlement_date: Date,
        *,
        rules: YieldCalculationRules,
        bump: float = 1e-4,
    ) -> "RiskMetrics":
        """Compute analytical and bumped risk measures from explicit cash flows.

        ``cashflows`` must already be settlement-relative bond cash flows with
        the bond's convention metadata attached.
        """

        projected_cashflows = list(cashflows)
        components = _analytical_risk_components(
            projected_cashflows,
            rules=rules,
            ytm=ytm,
            settlement_date=settlement_date,
        )
        if components.dirty_price == 0.0:
            return cls(
                modified_duration=Decimal(0),
                macaulay_duration=Decimal(0),
                convexity=Decimal(0),
                dv01=Decimal(0),
            )

        pricer = BondPricer()
        yield_rate = float(pricer._yield_to_engine_rate(ytm, rules=rules))
        price_up = float(
            pricer.engine.dirty_price_from_yield(
                projected_cashflows,
                yield_rate=yield_rate + bump,
                settlement_date=settlement_date,
                rules=rules,
            )
        )
        price_down = float(
            pricer.engine.dirty_price_from_yield(
                projected_cashflows,
                yield_rate=yield_rate - bump,
                settlement_date=settlement_date,
                rules=rules,
            )
        )
        first_derivative = (price_up - price_down) / (2.0 * bump)
        modified_duration = -(first_derivative / components.dirty_price)
        dv01 = -(first_derivative) * 1e-4

        return cls(
            modified_duration=Decimal(str(modified_duration)),
            macaulay_duration=Decimal(str(components.macaulay_duration)),
            convexity=Decimal(str(components.convexity)),
            dv01=Decimal(str(dv01)),
        )


DurationResult = RiskMetrics


__all__ = ["RiskMetrics", "DurationResult"]
