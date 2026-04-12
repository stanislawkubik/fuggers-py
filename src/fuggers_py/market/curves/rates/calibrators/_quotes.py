"""Private helpers for normalizing market quotes into fit rows."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto
from decimal import Decimal

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Compounding, Date, Price
from fuggers_py.market.quotes import (
    AnyInstrumentQuote,
    BondQuote,
    RawQuote,
    RepoQuote,
    SwapQuote,
)
from fuggers_py.reference.bonds.types import CompoundingKind
from fuggers_py.reference.bonds.types.tenor import Tenor

from ...errors import CurveConstructionError, InvalidCurveInput
from ..kernels.base import CurveKernel
from ..spec import CurveSpec

_DAY_COUNT_ALIASES = {
    "ACT/360": "ACT_360",
    "ACT/365F": "ACT_365_FIXED",
    "ACT/365FIXED": "ACT_365_FIXED",
    "ACT/365L": "ACT_365_LEAP",
    "ACT/365LEAP": "ACT_365_LEAP",
    "ACT/ACT": "ACT_ACT_ISDA",
    "ACT/ACTISDA": "ACT_ACT_ISDA",
    "ACT/ACTICMA": "ACT_ACT_ICMA",
    "ACT/ACTAFB": "ACT_ACT_AFB",
    "30/360": "THIRTY_360_US",
    "30/360US": "THIRTY_360_US",
    "30E/360": "THIRTY_360_E",
    "30/360E": "THIRTY_360_E",
    "30E/360ISDA": "THIRTY_360_E_ISDA",
    "30/360GERMAN": "THIRTY_360_GERMAN",
}


class QuoteValueKind(Enum):
    ZERO_RATE = auto()
    DISCOUNT_FACTOR = auto()
    BOND_YTM = auto()


@dataclass(frozen=True, slots=True)
class QuoteRow:
    instrument_id: str
    tenor: float
    value: float
    value_kind: QuoteValueKind
    observed_kind: str
    weight: float = 1.0
    compounding: Compounding = Compounding.CONTINUOUS
    source_quote: AnyInstrumentQuote | None = None


def _require_finite_numeric(value: object, *, name: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric):
        raise InvalidCurveInput(f"{name} must be finite.")
    return numeric


def _require_positive_tenor_string(text: str, *, quote_name: str) -> float:
    try:
        tenor = Tenor.parse(text)
    except Exception as exc:
        raise InvalidCurveInput(f"{quote_name} tenor must be a tenor string like '3M' or '5Y'.") from exc
    return tenor.to_years_approx()


def _tenor_from_dates(start: Date | None, end: Date | None, *, quote_name: str) -> float:
    if start is None or end is None:
        raise InvalidCurveInput(f"{quote_name} requires start_date and end_date, or one parseable term.")
    tenor = float(start.days_between(end)) / 365.0
    if tenor <= 0.0:
        raise InvalidCurveInput(f"{quote_name} must imply a tenor > 0.")
    return tenor


def _curve_day_count(spec: CurveSpec):
    key = spec.day_count.strip().upper().replace(" ", "")
    if key in DayCountConvention.__members__:
        return DayCountConvention[key].to_day_count()
    alias = _DAY_COUNT_ALIASES.get(key)
    if alias is not None:
        return DayCountConvention[alias].to_day_count()
    raise InvalidCurveInput(
        f"unsupported CurveSpec.day_count for quote-driven bond fitting: {spec.day_count}.",
    )


def _bond_quote_compounding(quote: BondQuote) -> Compounding:
    method = quote.instrument.rules().compounding
    if method.kind is CompoundingKind.CONTINUOUS:
        return Compounding.CONTINUOUS
    if method.kind in {CompoundingKind.SIMPLE, CompoundingKind.DISCOUNT}:
        return Compounding.SIMPLE
    frequency = 1 if method.frequency is None else int(method.frequency)
    if frequency == 1:
        return Compounding.ANNUAL
    if frequency == 2:
        return Compounding.SEMI_ANNUAL
    if frequency == 4:
        return Compounding.QUARTERLY
    if frequency == 12:
        return Compounding.MONTHLY
    return Compounding.ANNUAL


def _resolved_bond_settlement_date(quote: BondQuote) -> Date:
    try:
        return quote.resolved_settlement_date()
    except ValueError as exc:
        raise InvalidCurveInput(str(exc)) from exc


def _bond_clean_price_from_quote(quote: BondQuote, settlement_date: Date) -> tuple[Price, str]:
    if quote.clean_price is not None:
        return Price.new(quote.clean_price, quote.instrument.currency()), "BOND_CLEAN_PRICE_TO_YTM"
    if quote.dirty_price is not None:
        accrued = quote.accrued_interest
        if accrued is None:
            accrued = quote.instrument.accrued_interest(settlement_date)
        clean_price = Decimal(quote.dirty_price) - Decimal(accrued)
        return Price.new(clean_price, quote.instrument.currency()), "BOND_DIRTY_PRICE_TO_YTM"
    raise InvalidCurveInput(
        "BondQuote requires yield_to_maturity, clean_price, or dirty_price for quote-driven curve fitting.",
    )


def _swap_quote_row(quote: SwapQuote) -> QuoteRow:
    if quote.tenor is None:
        raise InvalidCurveInput("SwapQuote requires tenor for quote-driven curve fitting.")
    value = quote.quoted_value()
    if value is None:
        raise InvalidCurveInput("SwapQuote requires a quoted rate for quote-driven curve fitting.")
    return QuoteRow(
        instrument_id=str(quote.instrument_id),
        tenor=_require_positive_tenor_string(quote.tenor, quote_name="SwapQuote"),
        value=_require_finite_numeric(value, name="SwapQuote rate"),
        value_kind=QuoteValueKind.ZERO_RATE,
        observed_kind="SWAP_RATE",
        source_quote=quote,
    )


def _repo_quote_row(quote: RepoQuote) -> QuoteRow:
    value = quote.quoted_value()
    if value is None:
        raise InvalidCurveInput("RepoQuote requires a quoted rate for quote-driven curve fitting.")
    if quote.term is not None:
        try:
            tenor = _require_positive_tenor_string(quote.term, quote_name="RepoQuote")
        except InvalidCurveInput:
            tenor = _tenor_from_dates(quote.start_date, quote.end_date, quote_name="RepoQuote")
    else:
        tenor = _tenor_from_dates(quote.start_date, quote.end_date, quote_name="RepoQuote")
    return QuoteRow(
        instrument_id=str(quote.instrument_id),
        tenor=tenor,
        value=_require_finite_numeric(value, name="RepoQuote rate"),
        value_kind=QuoteValueKind.ZERO_RATE,
        observed_kind="REPO_RATE",
        source_quote=quote,
    )


def _raw_quote_error(_: RawQuote) -> QuoteRow:
    raise CurveConstructionError(
        "RawQuote is too generic for quote-driven curve fitting. Use a typed instrument quote such as SwapQuote or RepoQuote."
    )


def _bond_quote_row(quote: BondQuote, *, spec: CurveSpec) -> QuoteRow:
    settlement_date = _resolved_bond_settlement_date(quote)
    if settlement_date != spec.reference_date:
        raise InvalidCurveInput("BondQuote as_of must equal CurveSpec.reference_date for quote-driven curve fitting.")

    curve_day_count = _curve_day_count(spec)
    cash_flows = quote.instrument.cash_flows(settlement_date)
    if not cash_flows:
        raise InvalidCurveInput("BondQuote must have future cash flows after the settlement date.")
    tenor = float(curve_day_count.year_fraction(settlement_date, cash_flows[-1].date))
    if tenor <= 0.0:
        raise InvalidCurveInput("BondQuote must imply a tenor > 0.")

    if quote.yield_to_maturity is not None:
        market_ytm = _require_finite_numeric(quote.yield_to_maturity, name="BondQuote yield_to_maturity")
        observed_kind = "BOND_YTM"
    else:
        clean_price, observed_kind = _bond_clean_price_from_quote(quote, settlement_date)
        market_ytm = float(quote.instrument.yield_from_price(clean_price, settlement_date).ytm.value())

    return QuoteRow(
        instrument_id=str(quote.instrument_id),
        tenor=tenor,
        value=market_ytm,
        value_kind=QuoteValueKind.BOND_YTM,
        observed_kind=observed_kind,
        compounding=_bond_quote_compounding(quote),
        source_quote=quote,
    )


def _quote_row(quote: AnyInstrumentQuote, *, spec: CurveSpec) -> QuoteRow:
    if isinstance(quote, SwapQuote):
        return _swap_quote_row(quote)
    if isinstance(quote, RepoQuote):
        return _repo_quote_row(quote)
    if isinstance(quote, RawQuote):
        return _raw_quote_error(quote)
    if isinstance(quote, BondQuote):
        return _bond_quote_row(quote, spec=spec)
    raise CurveConstructionError(
        f"{type(quote).__name__} is not supported by the current quote-driven curve fitting path.",
    )


def _bond_clean_price_from_curve(quote: BondQuote, *, kernel: CurveKernel, spec: CurveSpec) -> Price:
    settlement_date = _resolved_bond_settlement_date(quote)
    if settlement_date != spec.reference_date:
        raise InvalidCurveInput("BondQuote as_of must equal CurveSpec.reference_date for quote-driven curve fitting.")

    curve_day_count = _curve_day_count(spec)
    dirty_price = Decimal(0)
    for cash_flow in quote.instrument.cash_flows(settlement_date):
        tenor = float(curve_day_count.year_fraction(spec.reference_date, cash_flow.date))
        discount_factor = Decimal(str(kernel.discount_factor_at(tenor)))
        dirty_price += cash_flow.factored_amount() * discount_factor
    clean_price = dirty_price - quote.instrument.accrued_interest(settlement_date)
    return Price.new(clean_price, quote.instrument.currency())


def model_quote_value(
    kernel: CurveKernel,
    quote_row: QuoteRow,
    *,
    spec: CurveSpec,
) -> float:
    if quote_row.value_kind is QuoteValueKind.ZERO_RATE:
        from ...conversion import ValueConverter

        return ValueConverter.convert_compounding(
            kernel.rate_at(quote_row.tenor),
            Compounding.CONTINUOUS,
            quote_row.compounding,
        )
    if quote_row.value_kind is QuoteValueKind.DISCOUNT_FACTOR:
        return kernel.discount_factor_at(quote_row.tenor)
    if quote_row.value_kind is QuoteValueKind.BOND_YTM:
        source_quote = quote_row.source_quote
        if not isinstance(source_quote, BondQuote):
            raise CurveConstructionError("Bond YTM quote rows must keep their source BondQuote.")
        clean_price = _bond_clean_price_from_curve(source_quote, kernel=kernel, spec=spec)
        model_ytm = source_quote.instrument.yield_from_price(
            clean_price,
            source_quote.resolved_settlement_date(),
        ).ytm
        return float(model_ytm.value())
    raise CurveConstructionError(f"unsupported quote value kind {quote_row.value_kind!r}.")


def normalized_quote_rows(
    quotes: Sequence[AnyInstrumentQuote],
    *,
    spec: CurveSpec,
    require_strictly_positive_tenor: bool,
) -> tuple[QuoteRow, ...]:
    if not quotes:
        raise InvalidCurveInput("curve fitting requires at least one quote.")
    rows = tuple(sorted((_quote_row(quote, spec=spec) for quote in quotes), key=lambda row: row.tenor))
    tenors = [row.tenor for row in rows]
    for left, right in zip(tenors, tenors[1:], strict=False):
        if right <= left:
            raise InvalidCurveInput("curve-fit quotes must have strictly increasing tenors.")
    if require_strictly_positive_tenor:
        for row in rows:
            if row.tenor <= 0.0:
                raise InvalidCurveInput("tenor must be finite and > 0.")
    else:
        for row in rows:
            if row.tenor < 0.0:
                raise InvalidCurveInput("tenor must be finite and >= 0.")
    return rows


__all__ = [
    "QuoteRow",
    "QuoteValueKind",
    "model_quote_value",
    "normalized_quote_rows",
]
