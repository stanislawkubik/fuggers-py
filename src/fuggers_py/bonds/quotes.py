"""Bond-domain quote records for the first-layer public facade."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType

from fuggers_py._core.ids import InstrumentId
from fuggers_py._core.quote_support import _coerce_decimal_fields
from fuggers_py._core.types import Currency, Date
from fuggers_py.bonds.traits import Bond


def deliverable_bpv_regressor(bpv: object, *, deliverable: bool) -> float:
    """Return the standard deliverability regressor encoding.

    This keeps ``BondQuote.regressors['deliverable_bpv']`` in one simple
    quote-level form: ``bpv`` when the bond is deliverable, otherwise ``0.0``.
    """

    if not deliverable:
        return 0.0
    try:
        numeric_bpv = float(bpv)
    except (TypeError, ValueError) as exc:
        raise ValueError("bpv must be a finite float-like value.") from exc
    if not math.isfinite(numeric_bpv):
        raise ValueError("bpv must be a finite float-like value.")
    return numeric_bpv


@dataclass(frozen=True, slots=True)
class BondQuote:
    """Market quote bound to a concrete bond instrument.

    ``regressors`` is the quote-level home for time-varying external variables
    used by ``GlobalFitCalibrator``. Examples include ``issue_size_bn``,
    ``issue_age_years``, ``deliverable_bpv``, and ``repo_specialness_bp``.
    Those values live on the quote, not on the bond instrument, because they
    can change from one observation date to the next.

    ``fit_weight`` is the quote-level weight used by
    ``GlobalFitCalibrator`` in its weighted least-squares fit.
    """

    instrument: Bond
    clean_price: Decimal | None = None
    dirty_price: Decimal | None = None
    accrued_interest: Decimal | None = None
    yield_to_maturity: Decimal | None = None
    yield_to_worst: Decimal | None = None
    as_of: Date | None = None
    source: str | None = None
    currency: Currency | None = None
    regressors: Mapping[str, float] | None = None
    fit_weight: float | None = None

    def __post_init__(self) -> None:
        _coerce_decimal_fields(
            self,
            "clean_price",
            "dirty_price",
            "accrued_interest",
            "yield_to_maturity",
            "yield_to_worst",
        )
        instrument_id = getattr(self.instrument, "instrument_id", None)
        if instrument_id is None:
            raise ValueError("BondQuote requires a concrete bond instrument with instrument_id.")
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        instrument_currency = self.instrument.currency()
        if self.currency is None:
            object.__setattr__(self, "currency", instrument_currency)
        elif self.currency != instrument_currency:
            raise ValueError("BondQuote currency must match the bond currency.")
        if self.regressors is not None:
            if not isinstance(self.regressors, Mapping):
                raise ValueError("BondQuote.regressors must be a mapping from regressor name to float.")
            normalized_regressors: dict[str, float] = {}
            for name, value in self.regressors.items():
                if not isinstance(name, str):
                    raise ValueError("BondQuote.regressors must use string regressor names.")
                try:
                    numeric_value = float(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError("BondQuote.regressors must map each regressor name to a finite float.") from exc
                if not math.isfinite(numeric_value):
                    raise ValueError("BondQuote.regressors must map each regressor name to a finite float.")
                normalized_regressors[name] = numeric_value
            object.__setattr__(self, "regressors", MappingProxyType(normalized_regressors))
        if self.fit_weight is not None:
            try:
                fit_weight = float(self.fit_weight)
            except (TypeError, ValueError) as exc:
                raise ValueError("BondQuote.fit_weight must be a finite float.") from exc
            if not math.isfinite(fit_weight):
                raise ValueError("BondQuote.fit_weight must be a finite float.")
            object.__setattr__(self, "fit_weight", fit_weight)

    @property
    def instrument_id(self) -> InstrumentId:
        """Return the instrument id of the bound bond."""
        instrument_id = getattr(self.instrument, "instrument_id", None)
        if instrument_id is None:
            raise ValueError("BondQuote requires a concrete bond instrument with instrument_id.")
        return InstrumentId.parse(instrument_id)

    def resolved_settlement_date(self) -> Date:
        """Return the pricing date carried by the quote."""
        if self.as_of is None:
            raise ValueError("BondQuote requires as_of.")
        return self.as_of


__all__ = [
    "BondQuote",
    "deliverable_bpv_regressor",
]
