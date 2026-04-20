"""Private helpers for normalizing market quotes into one fit-row type.

``QuoteRow`` stays the single normalized row shape for both bootstrap and
global-fit calibration. The calibration mode decides how bond observations are
represented inside that shared row type.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto
from decimal import Decimal

from fuggers_py.bonds.quotes import BondQuote
from fuggers_py.bonds.types import CompoundingKind
from fuggers_py._core.daycounts import DayCountConvention
from fuggers_py._core.types import Compounding, Date, Price
from fuggers_py.funding.quotes import RepoQuote
from fuggers_py.rates.quotes import SwapQuote

from ..errors import CurveConstructionError, InvalidCurveInput
from ..kernels.base import CurveKernel
from ..spec import CurveSpec
from .base import BondFitTarget, CalibrationMode, CalibrationSpec

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
    """Observed-value meaning for one normalized quote row.

    Bond rows can stay in yield space for bootstrap exact matching or move
    into clean-price or dirty-price space for bond global fit.
    """

    ZERO_RATE = auto()
    DISCOUNT_FACTOR = auto()
    BOND_CLEAN_PRICE = auto()
    BOND_DIRTY_PRICE = auto()
    BOND_YTM = auto()


class TargetSpaceCategory(Enum):
    """Unit category used to keep one global fit in one target space."""

    RATE = auto()
    DISCOUNT_FACTOR = auto()
    BOND_PRICE = auto()


@dataclass(frozen=True, slots=True)
class QuoteRow:
    """Single normalized quote row shared by bootstrap and global fit.

    ``regressor_values`` stores only the numeric values aligned to
    ``CalibrationSpec.regressor_names``. The row does not store regressor
    names, so the calibration spec stays the single source of regressor
    column order.
    """

    instrument_id: str
    tenor: float
    value: float
    value_kind: QuoteValueKind
    observed_kind: str
    weight: float = 1.0
    regressor_values: tuple[float, ...] = ()
    compounding: Compounding = Compounding.CONTINUOUS
    source_quote: object | None = None


def quote_value_target_space(value_kind: QuoteValueKind) -> TargetSpaceCategory:
    """Map one normalized quote kind into its global-fit target-space category."""

    if value_kind in {QuoteValueKind.ZERO_RATE, QuoteValueKind.BOND_YTM}:
        return TargetSpaceCategory.RATE
    if value_kind is QuoteValueKind.DISCOUNT_FACTOR:
        return TargetSpaceCategory.DISCOUNT_FACTOR
    if value_kind in {QuoteValueKind.BOND_CLEAN_PRICE, QuoteValueKind.BOND_DIRTY_PRICE}:
        return TargetSpaceCategory.BOND_PRICE
    raise CurveConstructionError(f"unsupported QuoteValueKind for target-space mapping: {value_kind!r}.")


def _require_finite_numeric(value: object, *, name: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric):
        raise InvalidCurveInput(f"{name} must be finite.")
    return numeric


def _require_positive_tenor_string(text: str, *, quote_name: str) -> float:
    from fuggers_py._core import Tenor

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
    if method.kind not in {CompoundingKind.PERIODIC, CompoundingKind.ACTUAL_PERIOD}:
        raise InvalidCurveInput(
            f"unsupported bond compounding kind {method.kind.name} for quote-driven curve fitting."
        )
    if method.frequency is None:
        raise InvalidCurveInput("periodic bond compounding requires frequency for quote-driven curve fitting.")
    frequency = int(method.frequency)
    if frequency == 1:
        return Compounding.ANNUAL
    if frequency == 2:
        return Compounding.SEMI_ANNUAL
    if frequency == 4:
        return Compounding.QUARTERLY
    if frequency == 12:
        return Compounding.MONTHLY
    raise InvalidCurveInput(
        f"unsupported bond compounding frequency {frequency} for quote-driven curve fitting."
    )


def _resolved_bond_settlement_date(quote: BondQuote) -> Date:
    try:
        return quote.resolved_settlement_date()
    except ValueError as exc:
        raise InvalidCurveInput(str(exc)) from exc


def _bond_accrued_interest(quote: BondQuote, settlement_date: Date) -> Decimal:
    accrued = quote.accrued_interest
    if accrued is not None:
        return Decimal(accrued)
    return Decimal(quote.instrument.accrued_interest(settlement_date))


def _bond_clean_price_from_quote(quote: BondQuote, settlement_date: Date) -> Price:
    if quote.clean_price is not None:
        return Price.new(quote.clean_price, quote.instrument.currency())
    if quote.dirty_price is not None:
        return Price.new(quote.dirty_price, quote.instrument.currency()).to_clean(
            _bond_accrued_interest(quote, settlement_date)
        )
    raise InvalidCurveInput(
        "BondQuote requires yield_to_maturity, clean_price, or dirty_price for quote-driven curve fitting.",
    )


def _bond_dirty_price_from_quote(quote: BondQuote, settlement_date: Date) -> Price:
    if quote.dirty_price is not None:
        return Price.new(quote.dirty_price, quote.instrument.currency())
    if quote.clean_price is not None:
        return Price.new(quote.clean_price, quote.instrument.currency()).to_dirty(
            _bond_accrued_interest(quote, settlement_date)
        )
    raise InvalidCurveInput(
        "BondQuote requires yield_to_maturity, clean_price, or dirty_price for quote-driven curve fitting.",
    )


def _aligned_bond_regressor_values(
    quote: BondQuote,
    *,
    calibration_spec: CalibrationSpec,
) -> tuple[float, ...]:
    """Return bond regressor values aligned to ``CalibrationSpec.regressor_names``."""

    if not calibration_spec.regressor_names:
        return ()
    regressors = quote.regressors
    if regressors is None:
        return tuple(0.0 for _ in calibration_spec.regressor_names)
    return tuple(
        _require_finite_numeric(
            regressors.get(name, 0.0),
            name=f"BondQuote.regressors[{name!r}]",
        )
        for name in calibration_spec.regressor_names
    )


def _quote_row_regressor_values(
    quote: object,
    *,
    calibration_spec: CalibrationSpec,
) -> tuple[float, ...]:
    if isinstance(quote, BondQuote):
        return _aligned_bond_regressor_values(quote, calibration_spec=calibration_spec)
    return tuple(0.0 for _ in calibration_spec.regressor_names)


def _quote_row_weight(quote: object) -> float:
    if isinstance(quote, BondQuote) and quote.fit_weight is not None:
        return _require_finite_numeric(quote.fit_weight, name="BondQuote.fit_weight")
    return 1.0


def _swap_quote_row(quote: SwapQuote, *, calibration_spec: CalibrationSpec) -> QuoteRow:
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
        regressor_values=_quote_row_regressor_values(quote, calibration_spec=calibration_spec),
        source_quote=quote,
    )


def _repo_quote_row(quote: RepoQuote, *, calibration_spec: CalibrationSpec) -> QuoteRow:
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
        regressor_values=_quote_row_regressor_values(quote, calibration_spec=calibration_spec),
        source_quote=quote,
    )


def _raw_quote_error(_: object) -> QuoteRow:
    raise CurveConstructionError(
        "RawQuote is too generic for quote-driven curve fitting. Use a typed instrument quote such as SwapQuote or RepoQuote."
    )


def _bond_quote_row(
    quote: BondQuote,
    *,
    spec: CurveSpec,
    calibration_spec: CalibrationSpec,
) -> QuoteRow:
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

    if calibration_spec.mode is CalibrationMode.BOOTSTRAP:
        if quote.yield_to_maturity is not None:
            value = _require_finite_numeric(quote.yield_to_maturity, name="BondQuote yield_to_maturity")
        else:
            value = _require_finite_numeric(
                quote.instrument.yield_from_price(
                    _bond_clean_price_from_quote(quote, settlement_date),
                    settlement_date,
                ).ytm.value(),
                name="BondQuote bootstrap yield proxy",
            )
        value_kind = QuoteValueKind.BOND_YTM
        observed_kind = "BOND_YTM"
    elif calibration_spec.mode is CalibrationMode.GLOBAL_FIT:
        price_present = quote.clean_price is not None or quote.dirty_price is not None
        if price_present and calibration_spec.bond_fit_target is BondFitTarget.CLEAN_PRICE:
            value = float(_bond_clean_price_from_quote(quote, settlement_date).as_percentage())
            value_kind = QuoteValueKind.BOND_CLEAN_PRICE
            observed_kind = "BOND_CLEAN_PRICE"
        elif price_present and calibration_spec.bond_fit_target is BondFitTarget.DIRTY_PRICE:
            value = float(_bond_dirty_price_from_quote(quote, settlement_date).as_percentage())
            value_kind = QuoteValueKind.BOND_DIRTY_PRICE
            observed_kind = "BOND_DIRTY_PRICE"
        elif not price_present and quote.yield_to_maturity is not None:
            value = _require_finite_numeric(quote.yield_to_maturity, name="BondQuote yield_to_maturity")
            value_kind = QuoteValueKind.BOND_YTM
            observed_kind = "BOND_YTM"
        elif not price_present:
            raise InvalidCurveInput(
                "global-fit bond normalization requires clean_price, dirty_price, or yield_to_maturity."
            )
        else:
            raise InvalidCurveInput(
                "global-fit bond normalization requires calibration_spec.bond_fit_target to be DIRTY_PRICE or CLEAN_PRICE."
            )
    else:
        raise InvalidCurveInput(
            "quote normalization requires calibration_spec.mode to be CalibrationMode.BOOTSTRAP or CalibrationMode.GLOBAL_FIT."
        )

    return QuoteRow(
        instrument_id=str(quote.instrument_id),
        tenor=tenor,
        value=value,
        value_kind=value_kind,
        observed_kind=observed_kind,
        weight=_quote_row_weight(quote),
        regressor_values=_quote_row_regressor_values(quote, calibration_spec=calibration_spec),
        compounding=_bond_quote_compounding(quote),
        source_quote=quote,
    )


def _quote_row(
    quote: object,
    *,
    spec: CurveSpec,
    calibration_spec: CalibrationSpec,
) -> QuoteRow:
    if isinstance(quote, SwapQuote):
        return _swap_quote_row(quote, calibration_spec=calibration_spec)
    if isinstance(quote, RepoQuote):
        return _repo_quote_row(quote, calibration_spec=calibration_spec)
    if type(quote).__name__ == "RawQuote":
        return _raw_quote_error(quote)
    if isinstance(quote, BondQuote):
        return _bond_quote_row(
            quote,
            spec=spec,
            calibration_spec=calibration_spec,
        )
    raise CurveConstructionError(
        f"{type(quote).__name__} is not supported by the current quote-driven curve fitting path.",
    )


def _bond_dirty_price_from_curve(quote: BondQuote, *, kernel: CurveKernel, spec: CurveSpec) -> Price:
    settlement_date = _resolved_bond_settlement_date(quote)
    if settlement_date != spec.reference_date:
        raise InvalidCurveInput("BondQuote as_of must equal CurveSpec.reference_date for quote-driven curve fitting.")

    curve_day_count = _curve_day_count(spec)
    dirty_price = Decimal(0)
    for cash_flow in quote.instrument.cash_flows(settlement_date):
        tenor = float(curve_day_count.year_fraction(spec.reference_date, cash_flow.date))
        discount_factor = Decimal(str(kernel.discount_factor_at(tenor)))
        dirty_price += cash_flow.factored_amount() * discount_factor
    return Price.new(dirty_price, quote.instrument.currency())


def _bond_clean_price_from_curve(quote: BondQuote, *, kernel: CurveKernel, spec: CurveSpec) -> Price:
    return _bond_dirty_price_from_curve(quote, kernel=kernel, spec=spec).to_clean(
        _bond_accrued_interest(quote, _resolved_bond_settlement_date(quote))
    )


def model_quote_value(
    kernel: CurveKernel,
    quote_row: QuoteRow,
    *,
    spec: CurveSpec,
) -> float:
    if quote_row.value_kind is QuoteValueKind.ZERO_RATE:
        from ..conversion import ValueConverter

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
    if quote_row.value_kind is QuoteValueKind.BOND_CLEAN_PRICE:
        source_quote = quote_row.source_quote
        if not isinstance(source_quote, BondQuote):
            raise CurveConstructionError("Bond clean-price quote rows must keep their source BondQuote.")
        return float(_bond_clean_price_from_curve(source_quote, kernel=kernel, spec=spec).as_percentage())
    if quote_row.value_kind is QuoteValueKind.BOND_DIRTY_PRICE:
        source_quote = quote_row.source_quote
        if not isinstance(source_quote, BondQuote):
            raise CurveConstructionError("Bond dirty-price quote rows must keep their source BondQuote.")
        return float(_bond_dirty_price_from_curve(source_quote, kernel=kernel, spec=spec).as_percentage())
    raise CurveConstructionError(f"unsupported quote value kind {quote_row.value_kind!r}.")


def normalized_quote_rows(
    quotes: Sequence[object],
    *,
    spec: CurveSpec,
    calibration_spec: CalibrationSpec,
    require_strictly_positive_tenor: bool,
) -> tuple[QuoteRow, ...]:
    if not quotes:
        raise InvalidCurveInput("curve fitting requires at least one quote.")
    if not isinstance(calibration_spec, CalibrationSpec):
        raise InvalidCurveInput("calibration_spec must be a CalibrationSpec.")
    rows = tuple(
        sorted(
            (
                _quote_row(
                    quote,
                    spec=spec,
                    calibration_spec=calibration_spec,
                )
                for quote in quotes
            ),
            key=lambda row: row.tenor,
        )
    )
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
    "TargetSpaceCategory",
    "QuoteValueKind",
    "model_quote_value",
    "normalized_quote_rows",
    "quote_value_target_space",
]
