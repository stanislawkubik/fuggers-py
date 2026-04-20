"""Bond pricing helpers for clean/dirty price and yield conversion.

The pricers in this module convert between yield-to-maturity, real yield for
inflation-linked bonds, and percent-of-par prices using the bond's configured
day-count, compounding, and settlement rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from fuggers_py._core import YieldCalculationRules
from fuggers_py.bonds.errors import BondPricingError
from fuggers_py.bonds.traits import Bond
from fuggers_py.bonds.types import CompoundingKind, CompoundingMethod
from fuggers_py._core.types import Compounding, Currency, Date, Price, Yield
from ._pricing_yield_engine import StandardYieldEngine, YieldEngineResult

if TYPE_CHECKING:  # pragma: no cover
    from fuggers_py.bonds.instruments import TipsBond


def _core_compounding_for(method: CompoundingMethod) -> Compounding:
    if method.kind is CompoundingKind.CONTINUOUS:
        return Compounding.CONTINUOUS
    if method.kind in {CompoundingKind.SIMPLE, CompoundingKind.DISCOUNT}:
        return Compounding.SIMPLE
    if method.frequency == 1:
        return Compounding.ANNUAL
    if method.frequency == 2:
        return Compounding.SEMI_ANNUAL
    if method.frequency == 4:
        return Compounding.QUARTERLY
    if method.frequency == 12:
        return Compounding.MONTHLY
    return Compounding.ANNUAL


@dataclass(frozen=True, slots=True)
class PriceResult:
    """Bond price decomposition at a settlement date.

    Dirty and clean prices are represented as
    :class:`~fuggers_py._core.types.Price` values in the bond currency. The
    ``present_value`` property exposes the dirty price as a raw percent-of-par
    decimal for downstream analytics that expect a numeric quote rather than a
    currency object.
    """

    dirty: Price
    clean: Price
    accrued: Decimal

    @property
    def dirty_price(self) -> Price:
        return self.dirty

    @property
    def clean_price(self) -> Price:
        return self.clean

    @property
    def accrued_interest(self) -> Decimal:
        return self.accrued

    @property
    def present_value(self) -> Decimal:
        """Return the dirty price as a percent-of-par decimal."""
        return self.dirty.as_percentage()


@dataclass(frozen=True, slots=True)
class YieldResult:
    """Bond yield result together with the lower-level engine output.

    ``ytm`` is returned in the bond's configured compounding convention. The
    nested engine result preserves the raw solver diagnostics used to reach the
    yield.
    """

    ytm: Yield
    engine: YieldEngineResult


@dataclass(frozen=True, slots=True)
class TipsPricer:
    """Real-yield pricer for :class:`~fuggers_py.bonds.instruments.TipsBond`.

    The class prices inflation-linked bonds off real yield and projected
    inflation-adjusted cash flows. Returned prices are in the bond currency and
    quoted in percent of par unless wrapped in :class:`~fuggers_py._core.types.Price`.
    """

    engine: StandardYieldEngine = StandardYieldEngine()

    def accrued_interest(
        self,
        bond: TipsBond,
        settlement_date: Date,
        *,
        fixing_source: object | None = None,
    ) -> Decimal:
        """Return settlement-date accrued interest on inflation-adjusted principal.

        The result is in currency units and reflects the bond's inflation-linked
        principal projection at the supplied settlement date.
        """

        return bond.accrued_interest(settlement_date, fixing_source=fixing_source)

    def present_value_from_real_yield(
        self,
        bond: TipsBond,
        real_yield: Yield,
        settlement_date: Date,
        *,
        fixing_source: object | None = None,
    ) -> Decimal:
        """Return the dirty price in percent of par from a real yield.

        The yield is interpreted as a real yield under the bond's configured
        compounding rules.
        """

        rules = bond.rules()
        y = BondPricer._yield_to_engine_rate(real_yield, rules=rules)
        dirty = self.engine.dirty_price_from_yield(
            bond.projected_cash_flows(fixing_source=fixing_source),
            yield_rate=y,
            settlement_date=settlement_date,
            rules=rules,
        )
        return Decimal(str(dirty))

    def dirty_price_from_real_yield(
        self,
        bond: TipsBond,
        real_yield: Yield,
        settlement_date: Date,
        *,
        fixing_source: object | None = None,
    ) -> Price:
        """Return the dirty price implied by ``real_yield``.

        The returned price is a currency-valued :class:`~fuggers_py._core.types.Price`.
        """

        dirty = self.present_value_from_real_yield(
            bond,
            real_yield,
            settlement_date,
            fixing_source=fixing_source,
        )
        return Price.new(dirty, bond.currency())

    def clean_price_from_real_yield(
        self,
        bond: TipsBond,
        real_yield: Yield,
        settlement_date: Date,
        *,
        fixing_source: object | None = None,
    ) -> Price:
        """Return the clean price implied by ``real_yield``.

        Accrued interest is removed from the dirty price on the bond's
        settlement date.
        """

        dirty = self.present_value_from_real_yield(
            bond,
            real_yield,
            settlement_date,
            fixing_source=fixing_source,
        )
        accrued = self.accrued_interest(bond, settlement_date, fixing_source=fixing_source)
        return Price.new(dirty - accrued, bond.currency())

    def price_from_real_yield(
        self,
        bond: TipsBond,
        real_yield: Yield,
        settlement_date: Date,
        *,
        fixing_source: object | None = None,
    ) -> PriceResult:
        """Return clean and dirty prices from a real yield.

        The result includes currency-valued clean and dirty prices plus
        accrued interest in currency units.
        """

        dirty = self.dirty_price_from_real_yield(
            bond,
            real_yield,
            settlement_date,
            fixing_source=fixing_source,
        )
        accrued = self.accrued_interest(bond, settlement_date, fixing_source=fixing_source)
        clean = dirty.as_percentage() - accrued
        return PriceResult(
            dirty=dirty,
            clean=Price.new(clean, bond.currency()),
            accrued=accrued,
        )

    def real_yield_from_clean_price(
        self,
        bond: TipsBond,
        clean_price: Price,
        settlement_date: Date,
        *,
        fixing_source: object | None = None,
    ) -> YieldResult:
        """Return the real yield implied by a clean price.

        ``clean_price`` must use the bond's currency. The returned yield is
        wrapped as a :class:`~fuggers_py._core.types.Yield` using the bond's
        compounding convention.
        """

        if clean_price.currency() != bond.currency():
            raise BondPricingError(reason="Price currency does not match bond currency.")

        rules = bond.rules()
        accrued = self.accrued_interest(bond, settlement_date, fixing_source=fixing_source)
        engine_res = self.engine.yield_from_price(
            bond.projected_cash_flows(fixing_source=fixing_source),
            clean_price=clean_price.as_percentage(),
            accrued=accrued,
            settlement_date=settlement_date,
            rules=rules,
        )
        compounding = _core_compounding_for(rules.compounding)
        ytm = Yield.new(Decimal(str(engine_res.yield_rate)), compounding=compounding)
        return YieldResult(ytm=ytm, engine=engine_res)

    def risk_metrics_from_real_yield(
        self,
        bond: TipsBond,
        real_yield: Yield,
        settlement_date: Date,
        *,
        fixing_source: object | None = None,
        bump: float = 1e-4,
    ):
        """Return duration, convexity, and DV01/PV01 with respect to real yield.

        The finite-difference bump is interpreted as a raw decimal yield shift;
        the returned DV01/PV01 is signed positive when price rises as yield
        falls.
        """

        from ._pricing_risk import RiskMetrics

        return RiskMetrics.from_projected_cashflows(
            bond.projected_cash_flows(fixing_source=fixing_source),
            real_yield,
            settlement_date,
            rules=bond.rules(),
            bump=bump,
        )


@dataclass(frozen=True, slots=True)
class BondPricer:
    """Convert between bond yields and clean/dirty prices.

    The pricer works in percent-of-par price space and maps yields through the
    bond's configured compounding convention before discounting cash flows.
    """

    engine: StandardYieldEngine = StandardYieldEngine()

    def price_from_yield(
        self,
        bond: Bond,
        ytm: Yield,
        settlement_date: Date,
        *,
        fixing_source: object | None = None,
    ) -> PriceResult:
        """Return dirty and clean prices from a yield-to-maturity input.

        The yield is converted to the bond's configured compounding convention
        before discounting. The dirty price is the percent-of-par present value;
        the clean price excludes accrued interest.
        """
        from fuggers_py.bonds.instruments import TipsBond

        if isinstance(bond, TipsBond):
            return TipsPricer(self.engine).price_from_real_yield(
                bond,
                ytm,
                settlement_date,
                fixing_source=fixing_source,
            )

        rules = bond.rules()
        y = self._yield_to_engine_rate(ytm, rules=rules)

        dirty = self.engine.dirty_price_from_yield(
            bond.cash_flows(),
            yield_rate=y,
            settlement_date=settlement_date,
            rules=rules,
        )
        accrued = bond.accrued_interest(settlement_date)
        clean = dirty - float(accrued)

        ccy = bond.currency()
        return PriceResult(
            dirty=Price.new(Decimal(str(dirty)), ccy),
            clean=Price.new(Decimal(str(clean)), ccy),
            accrued=accrued,
        )

    def yield_from_price(
        self,
        bond: Bond,
        clean_price: Price,
        settlement_date: Date,
        *,
        fixing_source: object | None = None,
    ) -> YieldResult:
        """Return the yield implied by a clean price and settlement date."""
        from fuggers_py.bonds.instruments import TipsBond

        if isinstance(bond, TipsBond):
            return TipsPricer(self.engine).real_yield_from_clean_price(
                bond,
                clean_price,
                settlement_date,
                fixing_source=fixing_source,
            )

        if clean_price.currency() != bond.currency():
            raise BondPricingError(reason="Price currency does not match bond currency.")

        rules = bond.rules()
        accrued = bond.accrued_interest(settlement_date)

        engine_res = self.engine.yield_from_price(
            bond.cash_flows(),
            clean_price=clean_price.as_percentage(),
            accrued=accrued,
            settlement_date=settlement_date,
            rules=rules,
        )

        compounding = _core_compounding_for(rules.compounding)
        ytm = Yield.new(Decimal(str(engine_res.yield_rate)), compounding=compounding)
        return YieldResult(ytm=ytm, engine=engine_res)

    def yield_to_maturity(
        self,
        bond: Bond,
        clean_price: Price,
        settlement_date: Date,
        *,
        fixing_source: object | None = None,
    ) -> Yield:
        """Return the yield implied by a clean price."""

        return self.yield_from_price(
            bond,
            clean_price,
            settlement_date,
            fixing_source=fixing_source,
        ).ytm

    @staticmethod
    def _yield_to_engine_rate(ytm: Yield, *, rules: YieldCalculationRules) -> float:
        """Convert a market yield into the engine's compounding convention."""
        target_compounding = _core_compounding_for(rules.compounding)
        y = ytm.convert_to(target_compounding).value()
        return float(y)


BondResult = PriceResult


__all__ = ["BondPricer", "BondResult", "PriceResult", "TipsPricer", "YieldResult"]
