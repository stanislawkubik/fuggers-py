"""Research-facing bond pricing router for the calc layer.

The router keeps the bond path focused on fixed, floating, and callable
instruments while preserving explicit clean-price semantics, batch failure
isolation, and readable pricing-path labels.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import TYPE_CHECKING

from fuggers_py._measures.functions import convexity, dv01, macaulay_duration, modified_duration, yield_to_maturity
from fuggers_py._measures.risk.duration.key_rate import KeyRateDurationCalculator
from fuggers_py._measures.spreads import (
    OASCalculator,
    BenchmarkKind,
    BenchmarkSpec,
    g_spread,
    g_spread_with_benchmark,
    i_spread,
    z_spread_from_curve,
)
from fuggers_py._measures.spreads.asw import ParParAssetSwap, ProceedsAssetSwap
from fuggers_py._measures.spreads.discount_margin import DiscountMarginCalculator
from fuggers_py._measures.yields.current import current_yield, current_yield_from_bond
from fuggers_py._products.bonds.instruments import CallableBond, FixedBond, FloatingRateNote, TipsBond, ZeroCouponBond
from fuggers_py._pricers.bonds.options import HullWhiteModel
from fuggers_py._pricers.bonds import TipsPricer
from fuggers_py._core.types import Date, Price
from fuggers_py._market.curve_support import discount_factor_at_date, parallel_bumped_curve, zero_rate_at_date
from fuggers_py._core.ids import InstrumentId
from fuggers_py._market.snapshot import MarketDataSnapshot
from fuggers_py._market.state import AnalyticsCurves
from fuggers_py.rates.indices import IndexFixingStore
from fuggers_py._market.sources import (
    FixingSource,
    InflationFixingSource,
    InMemoryFixingSource,
    MarketDataProvider,
    QuoteSource,
)
from fuggers_py._calc.output import BondQuoteOutput
from fuggers_py._calc.pricing_specs import PricingSpec, QuoteSide
from fuggers_py._reference.reference_data import BondReferenceData

from .errors import RoutingError

if TYPE_CHECKING:
    from fuggers_py.curves import DiscountingCurve


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, Price):
        return value.as_percentage()
    return Decimal(str(value))


def _curve_supports_discounting(curve: object | None) -> bool:
    return curve is not None and all(
        hasattr(curve, attribute)
        for attribute in ("spec", "reference_date", "discount_factor_at", "zero_rate_at", "forward_rate_between")
    )


@dataclass(frozen=True, slots=True)
class PricingInput:
    """Single pricing request used by the batch router.

    Parameters
    ----------
    instrument:
        Instrument or bond reference data to price.
    settlement_date:
        Economic settlement date for accrual and discounting.
    market_price:
        Input market price. For fixed and callable bonds this is interpreted as
        a clean price unless the pricing spec says otherwise.
    pricing_spec:
        Optional pricing directives.
    curves:
        Optional curve bundle used by the pricing path.
    market_data:
        Optional market-data snapshot or provider used to resolve quotes and
        fixings.
    reference_data:
        Optional reference data used to resolve instruments and metadata.
    instrument_id:
        Explicit instrument identifier override.

    Notes
    -----
    The request object keeps the original batch shape so failures can be tied
    back to the request that produced them.
    """

    instrument: object
    settlement_date: Date
    market_price: object | None = None
    pricing_spec: PricingSpec | None = None
    curves: AnalyticsCurves | None = None
    market_data: MarketDataSnapshot | MarketDataProvider | QuoteSource | FixingSource | InflationFixingSource | None = None
    reference_data: BondReferenceData | dict[InstrumentId, BondReferenceData] | None = None
    instrument_id: InstrumentId | str | None = None

    def resolved_instrument_id(self) -> InstrumentId | None:
        """Return the best-effort instrument identifier for the request."""
        if self.instrument_id is not None:
            return self.instrument_id if isinstance(self.instrument_id, InstrumentId) else InstrumentId.parse(self.instrument_id)
        if isinstance(self.instrument, InstrumentId):
            return self.instrument
        if isinstance(self.instrument, str):
            return InstrumentId.parse(self.instrument)
        if isinstance(self.instrument, BondReferenceData):
            return self.instrument.instrument_id
        candidate = getattr(self.instrument, "instrument_id", None)
        if candidate is not None:
            return candidate if isinstance(candidate, InstrumentId) else InstrumentId.parse(candidate)
        return None

    def key(self, index: int) -> str:
        """Return a stable batch key for the request."""
        resolved = self.resolved_instrument_id()
        if resolved is not None:
            return resolved.as_str()
        return f"batch:{index}"


@dataclass(frozen=True, slots=True)
class PricingFailure:
    """Structured failure record returned by batch pricing.

    The record keeps the batch key, exception type, and message so a caller can
    report a partial failure without losing the request identity.
    """

    key: str
    error_type: str
    message: str


@dataclass(frozen=True, slots=True)
class BatchPricingResult:
    """Container for successful and failed batch-pricing outputs.

    Successes and failures preserve insertion order to match the original batch
    request as closely as possible.
    """

    outputs: dict[str, BondQuoteOutput] = field(default_factory=dict)
    errors: dict[str, PricingFailure] = field(default_factory=dict)

    @property
    def successes(self) -> tuple[BondQuoteOutput, ...]:
        """Return the successful outputs in insertion order."""
        return tuple(self.outputs.values())

    @property
    def failures(self) -> tuple[PricingFailure, ...]:
        """Return the structured failures in insertion order."""
        return tuple(self.errors.values())


@dataclass(frozen=True, slots=True)
class PricingRouter:
    """Route bond instruments to the appropriate pricing path.

    The router keeps fixed, floating, TIPS, and callable bond logic in one
    place while preserving clean-price semantics, curve lookups, and
    failure-isolated batch behavior.
    """

    def price(
        self,
        instrument,
        settlement_date: Date,
        *,
        market_price: object | None = None,
        pricing_spec: PricingSpec | None = None,
        curves: AnalyticsCurves | None = None,
        market_data: MarketDataSnapshot | MarketDataProvider | QuoteSource | FixingSource | InflationFixingSource | None = None,
        reference_data: BondReferenceData | dict[InstrumentId, BondReferenceData] | None = None,
        instrument_id: InstrumentId | str | None = None,
    ) -> BondQuoteOutput:
        """Price a single bond instrument.

        Fixed and callable bonds use clean-price semantics by default. Floating
        rate notes use their coupon/fixing path and may interpret the supplied
        market price as dirty or clean depending on the pricing spec.

        The router resolves instrument references, sources quotes and fixings
        from the provided market-data inputs when needed, and raises
        :class:`RoutingError` when the instrument type is unsupported.
        """
        spec = pricing_spec or PricingSpec()
        resolved_instrument, resolved_id = self._resolve_instrument_and_id(
            instrument,
            reference_data=reference_data,
            instrument_id=instrument_id,
        )
        if isinstance(resolved_instrument, FloatingRateNote):
            return self.price_floating(
                resolved_instrument,
                settlement_date,
                instrument_id=resolved_id,
                market_price=market_price,
                pricing_spec=spec,
                curves=curves,
                market_data=market_data,
            )
        if isinstance(resolved_instrument, CallableBond) and resolved_instrument.call_schedule is not None:
            return self.price_callable(
                resolved_instrument,
                settlement_date,
                instrument_id=resolved_id,
                market_price=market_price,
                pricing_spec=spec,
                curves=curves,
                market_data=market_data,
            )
        if isinstance(resolved_instrument, TipsBond):
            return self.price_tips(
                resolved_instrument,
                settlement_date,
                instrument_id=resolved_id,
                market_price=market_price,
                pricing_spec=spec,
                market_data=market_data,
            )
        if isinstance(resolved_instrument, (FixedBond, ZeroCouponBond, CallableBond)):
            return self.price_fixed(
                resolved_instrument,
                settlement_date,
                instrument_id=resolved_id,
                market_price=market_price,
                pricing_spec=spec,
                curves=curves,
                market_data=market_data,
        )
        raise RoutingError(f"Unsupported instrument type: {type(resolved_instrument).__name__}.")

    def price_batch(self, inputs: list[PricingInput] | tuple[PricingInput, ...]) -> BatchPricingResult:
        """Price a batch of bonds and isolate failures per request.

        Each request is priced independently. A failure in one item is captured
        as a :class:`PricingFailure` entry without aborting the remaining batch.
        """
        outputs: dict[str, BondQuoteOutput] = {}
        errors: dict[str, PricingFailure] = {}
        for index, pricing_input in enumerate(inputs):
            key = pricing_input.key(index)
            try:
                outputs[key] = self.price(
                    pricing_input.instrument,
                    pricing_input.settlement_date,
                    market_price=pricing_input.market_price,
                    pricing_spec=pricing_input.pricing_spec,
                    curves=pricing_input.curves,
                    market_data=pricing_input.market_data,
                    reference_data=pricing_input.reference_data,
                    instrument_id=pricing_input.instrument_id,
                )
            except Exception as exc:
                errors[key] = PricingFailure(
                    key=key,
                    error_type=type(exc).__name__,
                    message=str(exc),
                )
        return BatchPricingResult(outputs=outputs, errors=errors)

    def price_fixed(
        self,
        instrument: FixedBond | ZeroCouponBond | CallableBond,
        settlement_date: Date,
        *,
        instrument_id: InstrumentId | None = None,
        market_price: object | None = None,
        pricing_spec: PricingSpec | None = None,
        curves: AnalyticsCurves | None = None,
        market_data: MarketDataSnapshot | MarketDataProvider | QuoteSource | FixingSource | InflationFixingSource | None = None,
    ) -> BondQuoteOutput:
        """Price a fixed, zero-coupon, or callable bond from a clean price.

        The input market price is treated as clean unless ``pricing_spec``
        explicitly marks it as dirty. The method derives dirty price, accrued
        interest, yields, and optional risk measures from that clean-price
        anchor. When market data is supplied, the method can source the quote
        side requested by the pricing spec instead of requiring the caller to
        pre-resolve the market price.

        Parameters
        ----------
        instrument:
            Fixed-rate, zero-coupon, or callable bond to price on the fixed
            bond path.
        settlement_date:
            Settlement date used for accrual, pricing, and risk measures.
        market_price:
            Optional market anchor. By default this is interpreted as a clean
            price in percent of par.
        pricing_spec:
            Optional directives controlling risk, spread, and quote-side logic.
        curves:
            Optional curve bundle used for spread and key-rate calculations.
        market_data:
            Optional source of quotes and fixings when ``market_price`` is not
            supplied directly.

        Returns
        -------
        BondQuoteOutput
            Structured output with clean and dirty prices, yield measures, and
            optional risk and spread fields.
        """
        spec = pricing_spec or PricingSpec()
        active_curves = curves or AnalyticsCurves()
        resolved_market_price = market_price or self._market_price_from_source(market_data, instrument_id, spec.quote_side)
        clean_price, dirty_price, accrued = self._clean_dirty_accrued(
            instrument,
            settlement_date,
            market_price=resolved_market_price,
            market_price_is_dirty=bool(spec.market_price_is_dirty),
            discount_curve=active_curves.discount_curve,
        )
        price = Price.new(clean_price, instrument.currency())
        ytm_obj = yield_to_maturity(instrument, price, settlement_date)
        ytm = ytm_obj.value()
        ytw = self._yield_to_worst(instrument, clean_price, settlement_date, spec)
        output = BondQuoteOutput(
            instrument_id=instrument_id,
            pricing_path="fixed",
            clean_price=clean_price,
            dirty_price=dirty_price,
            accrued_interest=accrued,
            yield_to_maturity=ytm,
            yield_to_worst=ytw,
            current_yield=self._current_yield(instrument, clean_price, spec),
            modified_duration=modified_duration(instrument, ytm_obj, settlement_date) if spec.compute_risk else None,
            macaulay_duration=macaulay_duration(instrument, ytm_obj, settlement_date) if spec.compute_risk else None,
            dv01=dv01(instrument, ytm_obj, settlement_date) if spec.compute_risk else None,
            convexity=convexity(instrument, ytm_obj, settlement_date) if spec.compute_risk else None,
            key_rate_durations=self._key_rate_durations(instrument, active_curves.discount_curve, settlement_date, spec),
        )
        return self._with_spreads(output, instrument, settlement_date, ytm=ytm, dirty_price=dirty_price, curves=active_curves, spec=spec)

    def price_tips(
        self,
        instrument: TipsBond,
        settlement_date: Date,
        *,
        instrument_id: InstrumentId | None = None,
        market_price: object | None = None,
        pricing_spec: PricingSpec | None = None,
        market_data: MarketDataSnapshot | MarketDataProvider | QuoteSource | FixingSource | InflationFixingSource | None = None,
    ) -> BondQuoteOutput:
        """Price a TIPS bond from a clean or dirty market price and solve a real yield.

        The pricing path uses inflation fixings from the provided market-data
        inputs when available and reports the projected next coupon in real
        terms.

        Returns
        -------
        BondQuoteOutput
            Structured output where ``yield_to_maturity`` is the real yield.
            ``projected_next_coupon`` follows the inflation-linked coupon path
            implied by the available fixings.
        """

        spec = pricing_spec or PricingSpec()
        resolved_market_price = market_price or self._market_price_from_source(market_data, instrument_id, spec.quote_side)
        if resolved_market_price is None:
            raise RoutingError("TIPS pricing requires a market clean/dirty price or quote source.")

        fixing_source = self._inflation_fixing_source(market_data)
        pricer = TipsPricer()
        accrued = pricer.accrued_interest(instrument, settlement_date, fixing_source=fixing_source)
        market_value = _to_decimal(resolved_market_price)
        if bool(spec.market_price_is_dirty):
            dirty_price = market_value
            clean_price = dirty_price - accrued
        else:
            clean_price = market_value
            dirty_price = clean_price + accrued

        real_yield = pricer.real_yield_from_clean_price(
            instrument,
            Price.new(clean_price, instrument.currency()),
            settlement_date,
            fixing_source=fixing_source,
        ).ytm

        projected_coupons = instrument.projected_coupon_cash_flows(
            fixing_source=fixing_source,
            settlement_date=settlement_date,
        )
        next_coupon = None if not projected_coupons else projected_coupons[0].factored_amount()

        risk = None
        if spec.compute_risk:
            risk = pricer.risk_metrics_from_real_yield(
                instrument,
                real_yield,
                settlement_date,
                fixing_source=fixing_source,
            )

        return BondQuoteOutput(
            instrument_id=instrument_id,
            pricing_path="tips_real_yield",
            clean_price=clean_price,
            dirty_price=dirty_price,
            accrued_interest=accrued,
            yield_to_maturity=real_yield.value(),
            modified_duration=None if risk is None else risk.modified_duration,
            macaulay_duration=None if risk is None else risk.macaulay_duration,
            dv01=None if risk is None else risk.dv01,
            convexity=None if risk is None else risk.convexity,
            projected_next_coupon=next_coupon,
            notes=("yield_to_maturity is real yield",),
        )

    def price_callable(
        self,
        instrument: CallableBond,
        settlement_date: Date,
        *,
        instrument_id: InstrumentId | None = None,
        market_price: object | None = None,
        pricing_spec: PricingSpec | None = None,
        curves: AnalyticsCurves | None = None,
        market_data: MarketDataSnapshot | MarketDataProvider | QuoteSource | FixingSource | InflationFixingSource | None = None,
    ) -> BondQuoteOutput:
        """Price a callable bond and optionally attach an OAS analysis.

        Callable bonds are priced through the Hull-White helper so option value,
        yield-to-worst, and callable spreads stay tied to the same pricing
        path.

        Notes
        -----
        The base clean-price path is the same as :meth:`price_fixed`. When
        ``route_callable_with_oas`` is enabled and a discount curve is
        available, the router also fills ``oas``, ``effective_duration``,
        ``effective_convexity``, and ``option_value``.
        """
        spec = pricing_spec or PricingSpec()
        base_output = self.price_fixed(
            instrument,
            settlement_date,
            instrument_id=instrument_id,
            market_price=market_price,
            pricing_spec=spec,
            curves=curves,
            market_data=market_data,
        )
        active_curves = curves or AnalyticsCurves()
        if not spec.route_callable_with_oas or active_curves.discount_curve is None:
            return replace(base_output, pricing_path="callable")
        model = HullWhiteModel(
            mean_reversion=spec.callable_mean_reversion,
            volatility=spec.callable_volatility,
            term_structure=active_curves.discount_curve,
        )
        calculator = OASCalculator(model=model)
        oas = calculator.calculate(instrument, base_output.dirty_price or Decimal(0), settlement_date)
        return replace(
            base_output,
            pricing_path="callable",
            oas=oas,
            effective_duration=calculator.effective_duration(instrument, oas, settlement_date),
            effective_convexity=calculator.effective_convexity(instrument, oas, settlement_date),
            option_value=calculator.option_value(instrument, oas, settlement_date),
        )

    def price_floating(
        self,
        instrument: FloatingRateNote,
        settlement_date: Date,
        *,
        instrument_id: InstrumentId | None = None,
        market_price: object | None = None,
        pricing_spec: PricingSpec | None = None,
        curves: AnalyticsCurves | None = None,
        market_data: MarketDataSnapshot | QuoteSource | FixingSource | InflationFixingSource | None = None,
    ) -> BondQuoteOutput:
        """Price a floating-rate note using fixing-aware accrued-interest logic.

        Floating notes can source market prices, curve inputs, and fixings from
        the supplied market-data bundle before the coupon path is evaluated.

        Notes
        -----
        The output uses the floating-rate path conventions: ``discount_margin``
        and ``spread_duration`` are only populated when both forward and
        discount curves are available, and projected coupon/reset fields depend
        on the available fixing history and forward curve.
        """
        spec = pricing_spec or PricingSpec()
        active_curves = curves or AnalyticsCurves()
        fixing_store = self._fixing_store(market_data)
        resolved_market_price = market_price or self._market_price_from_source(market_data, instrument_id, spec.quote_side)
        accrued = instrument.accrued_interest(
            settlement_date,
            fixing_store=fixing_store,
            forward_curve=active_curves.forward_curve,
        )
        dirty_price = self._floating_dirty_price(
            instrument,
            settlement_date,
            market_price=resolved_market_price,
            market_price_is_dirty=spec.market_price_is_dirty,
            curves=active_curves,
            fixing_store=fixing_store,
        )
        clean_price = dirty_price - accrued

        discount_margin = None
        spread_duration = None
        modified_duration_value = None
        dv01_value = None
        convexity_value = None
        if spec.route_floating_with_discount_margin and active_curves.forward_curve is not None and active_curves.discount_curve is not None:
            calculator = DiscountMarginCalculator(
                forward_curve=active_curves.forward_curve,
                discount_curve=active_curves.discount_curve,
            )
            discount_margin = calculator.calculate(instrument, dirty_price, settlement_date)
            spread_duration = calculator.spread_duration(instrument, discount_margin, settlement_date)
        if active_curves.discount_curve is not None and active_curves.forward_curve is not None:
            modified_duration_value, dv01_value, convexity_value = self._floating_rate_risk(
                instrument,
                settlement_date,
                curves=active_curves,
                fixing_store=fixing_store,
            )

        projected_flows = instrument.cash_flows_with_fixings(
            fixing_store or IndexFixingStore(),
            settlement_date=settlement_date,
            forward_curve=active_curves.forward_curve,
        ) if fixing_store is not None else instrument.projected_cash_flows(
            active_curves.forward_curve,
            settlement_date=settlement_date,
        )
        next_coupon = None
        next_reset_date = None
        if projected_flows:
            first = projected_flows[0]
            coupon_component = first.factored_amount() - (instrument.notional() if first.is_principal() else Decimal(0))
            next_coupon = coupon_component
            next_reset_date = first.accrual_start or first.date

        return BondQuoteOutput(
            instrument_id=instrument_id,
            pricing_path="floating_rate",
            clean_price=clean_price,
            dirty_price=dirty_price,
            accrued_interest=accrued,
            current_yield=self._current_yield(instrument, clean_price, spec),
            modified_duration=modified_duration_value,
            dv01=dv01_value,
            convexity=convexity_value,
            discount_margin=discount_margin,
            spread_duration=spread_duration,
            projected_next_coupon=next_coupon,
            next_reset_date=next_reset_date,
            notes=("historical fixings applied",) if fixing_store is not None else (),
        )

    def _resolve_instrument_and_id(
        self,
        instrument,
        *,
        reference_data: BondReferenceData | dict[InstrumentId, BondReferenceData] | None,
        instrument_id: InstrumentId | str | None,
    ) -> tuple[object, InstrumentId | None]:
        resolved_id = None if instrument_id is None else (
            instrument_id if isinstance(instrument_id, InstrumentId) else InstrumentId.parse(instrument_id)
        )
        if isinstance(instrument, BondReferenceData):
            return instrument.to_instrument(), instrument.instrument_id
        if isinstance(instrument, InstrumentId):
            resolved_id = instrument
            instrument = instrument
        if isinstance(instrument, str):
            resolved_id = InstrumentId.parse(instrument)
        if resolved_id is None:
            candidate = getattr(instrument, "instrument_id", None)
            if candidate is not None:
                resolved_id = candidate if isinstance(candidate, InstrumentId) else InstrumentId.parse(candidate)
        if resolved_id is not None and reference_data is not None:
            if isinstance(reference_data, BondReferenceData):
                return reference_data.to_instrument(), reference_data.instrument_id
            if resolved_id in reference_data:
                return reference_data[resolved_id].to_instrument(), resolved_id
        return instrument, resolved_id

    def _clean_dirty_accrued(
        self,
        instrument,
        settlement_date: Date,
        *,
        market_price: object | None,
        market_price_is_dirty: bool,
        discount_curve: DiscountingCurve | None,
    ) -> tuple[Decimal, Decimal, Decimal]:
        accrued = instrument.accrued_interest(settlement_date)
        if market_price is not None:
            value = _to_decimal(market_price)
            if market_price_is_dirty:
                return value - accrued, value, accrued
            return value, value + accrued, accrued
        if discount_curve is None:
            raise RoutingError("A market price or discount curve is required.")
        pv = Decimal(0)
        df_settle = discount_factor_at_date(discount_curve, settlement_date)
        for cf in instrument.cash_flows(settlement_date):
            pv += cf.factored_amount() * discount_factor_at_date(discount_curve, cf.date) / df_settle
        return pv - accrued, pv, accrued

    def _floating_dirty_price(
        self,
        instrument: FloatingRateNote,
        settlement_date: Date,
        *,
        market_price: object | None,
        market_price_is_dirty: bool | None,
        curves: AnalyticsCurves,
        fixing_store: IndexFixingStore | None,
    ) -> Decimal:
        if market_price is not None:
            value = _to_decimal(market_price)
            if market_price_is_dirty is False:
                return value + instrument.accrued_interest(
                    settlement_date,
                    fixing_store=fixing_store,
                    forward_curve=curves.forward_curve,
                )
            return value
        if curves.discount_curve is None or curves.forward_curve is None:
            raise RoutingError("Floating-rate pricing requires either a dirty market price or forward/discount curves.")
        projected = instrument.cash_flows_with_fixings(
            fixing_store or IndexFixingStore(),
            settlement_date=settlement_date,
            forward_curve=curves.forward_curve,
        ) if fixing_store is not None else instrument.projected_cash_flows(curves.forward_curve, settlement_date=settlement_date)
        df_settle = discount_factor_at_date(curves.discount_curve, settlement_date)
        return sum(
            (cf.factored_amount() * discount_factor_at_date(curves.discount_curve, cf.date) / df_settle for cf in projected),
            Decimal(0),
        )

    def _fixing_store(
        self,
        market_data: MarketDataSnapshot | MarketDataProvider | QuoteSource | FixingSource | InflationFixingSource | None,
    ) -> IndexFixingStore | None:
        if market_data is None:
            return None
        if isinstance(market_data, MarketDataSnapshot):
            return market_data.fixing_source().to_fixing_store()
        if isinstance(market_data, InMemoryFixingSource):
            return market_data.to_fixing_store()
        if hasattr(market_data, "to_fixing_store"):
            return getattr(market_data, "to_fixing_store")()
        return None

    def _inflation_fixing_source(
        self,
        market_data: MarketDataSnapshot | MarketDataProvider | QuoteSource | FixingSource | InflationFixingSource | None,
    ) -> InflationFixingSource | None:
        if market_data is None:
            return None
        if isinstance(market_data, MarketDataSnapshot):
            return market_data.inflation_fixing_source()
        if isinstance(market_data, InflationFixingSource):
            return market_data
        if hasattr(market_data, "get_inflation_fixing"):
            return market_data  # type: ignore[return-value]
        return None

    def _market_price_from_source(
        self,
        market_data: MarketDataSnapshot | MarketDataProvider | QuoteSource | FixingSource | InflationFixingSource | None,
        instrument_id: InstrumentId | None,
        side: QuoteSide,
    ) -> Decimal | None:
        if market_data is None or instrument_id is None:
            return None
        if isinstance(market_data, MarketDataSnapshot):
            quote = market_data.quote_source().get_quote(instrument_id, side)
            return None if quote is None else quote.value
        if hasattr(market_data, "get_quote"):
            quote = getattr(market_data, "get_quote")(instrument_id, side)
            return None if quote is None else quote.value
        return None

    def _floating_rate_risk(
        self,
        instrument: FloatingRateNote,
        settlement_date: Date,
        *,
        curves: AnalyticsCurves,
        fixing_store: IndexFixingStore | None,
        bump: float = 1e-4,
    ) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
        base_curve = curves.discount_curve
        if base_curve is None:
            return None, None, None
        base_dirty_price = self._floating_dirty_price(
            instrument,
            settlement_date,
            market_price=None,
            market_price_is_dirty=True,
            curves=curves,
            fixing_store=fixing_store,
        )
        bumped_up = AnalyticsCurves(
            discount_curve=parallel_bumped_curve(base_curve, bump),
            forward_curve=curves.forward_curve,
            government_curve=curves.government_curve,
            benchmark_curve=curves.benchmark_curve,
        )
        bumped_down = AnalyticsCurves(
            discount_curve=parallel_bumped_curve(base_curve, -bump),
            forward_curve=curves.forward_curve,
            government_curve=curves.government_curve,
            benchmark_curve=curves.benchmark_curve,
        )
        price_up = self._floating_dirty_price(
            instrument,
            settlement_date,
            market_price=None,
            market_price_is_dirty=True,
            curves=bumped_up,
            fixing_store=fixing_store,
        )
        price_down = self._floating_dirty_price(
            instrument,
            settlement_date,
            market_price=None,
            market_price_is_dirty=True,
            curves=bumped_down,
            fixing_store=fixing_store,
        )
        if base_dirty_price == 0:
            return Decimal(0), Decimal(0), Decimal(0)
        dv01_value = (price_down - price_up) / Decimal(2)
        modified = dv01_value / (base_dirty_price * Decimal(str(bump)))
        convexity_value = (price_up + price_down - (Decimal(2) * base_dirty_price)) / (
            base_dirty_price * Decimal(str(bump * bump))
        )
        return modified, dv01_value, convexity_value

    def _current_yield(self, instrument, clean_price: Decimal, spec: PricingSpec) -> Decimal | None:
        if not spec.compute_current_yield:
            return None
        if hasattr(instrument, "coupon_rate"):
            return current_yield_from_bond(instrument, clean_price)
        base_bond = getattr(instrument, "base_bond", None)
        if base_bond is not None and hasattr(base_bond, "coupon_rate"):
            return current_yield_from_bond(base_bond, clean_price)
        if hasattr(instrument, "current_coupon_rate"):
            return current_yield(instrument.current_coupon_rate(), clean_price)
        return None

    def _yield_to_worst(self, instrument, clean_price: Decimal, settlement_date: Date, spec: PricingSpec) -> Decimal | None:
        if not spec.compute_yield_to_worst or not hasattr(instrument, "yield_to_worst"):
            return None
        return instrument.yield_to_worst(clean_price, settlement_date)

    def _key_rate_durations(
        self,
        instrument,
        curve: DiscountingCurve | None,
        settlement_date: Date,
        spec: PricingSpec,
    ) -> dict[str, Decimal]:
        if not spec.compute_key_rates or curve is None:
            return {}
        result = KeyRateDurationCalculator().calculate(instrument, curve, settlement_date)
        return {str(item.tenor): item.duration for item in result.items}

    def _with_spreads(
        self,
        output: BondQuoteOutput,
        instrument,
        settlement_date: Date,
        *,
        ytm: Decimal,
        dirty_price: Decimal,
        curves: AnalyticsCurves,
        spec: PricingSpec,
    ) -> BondQuoteOutput:
        if not spec.compute_spreads:
            return output
        z_value = None
        if curves.discount_curve is not None:
            z_value = z_spread_from_curve(
                instrument.cash_flows(),
                dirty_price=dirty_price,
                curve=curves.discount_curve,
                settlement_date=settlement_date,
            )
        g_value = None
        benchmark_info = None
        if curves.government_curve is not None:
            if hasattr(curves.government_curve, "yield_for_date"):
                if spec.benchmark_reference is not None and spec.benchmark_reference.tenor is not None:
                    benchmark = BenchmarkSpec(
                        kind=BenchmarkKind.TENOR,
                        tenor=spec.benchmark_reference.tenor_object(),
                    )
                    g_value = g_spread_with_benchmark(
                        ytm,
                        curves.government_curve,
                        instrument.maturity_date(),
                        benchmark=benchmark,
                    )
                    benchmark_info = f"government:{spec.benchmark_reference.tenor}"
                else:
                    g_value = g_spread_with_benchmark(ytm, curves.government_curve, instrument.maturity_date())
                    benchmark_info = "government:interpolated"
            else:
                g_value = g_spread(ytm, zero_rate_at_date(curves.government_curve, instrument.maturity_date()))
                benchmark_info = "government:curve"
        i_value = None
        asw_value = None
        if curves.benchmark_curve is not None:
            if _curve_supports_discounting(curves.benchmark_curve):
                i_value = i_spread(ytm, zero_rate_at_date(curves.benchmark_curve, instrument.maturity_date()))
            if spec.include_asset_swap and isinstance(instrument, FixedBond):
                calculator = ParParAssetSwap(curves.benchmark_curve)
                if spec.asset_swap_type.value == "PROCEEDS":
                    calculator = ProceedsAssetSwap(curves.benchmark_curve)
                asw_value = calculator.calculate(instrument, dirty_price, settlement_date)
                benchmark_info = "benchmark:curve"
        return replace(
            output,
            z_spread=z_value,
            g_spread=g_value,
            i_spread=i_value,
            asset_swap_spread=asw_value,
            benchmark_info=benchmark_info,
        )


__all__ = ["BatchPricingResult", "PricingFailure", "PricingInput", "PricingRouter"]
