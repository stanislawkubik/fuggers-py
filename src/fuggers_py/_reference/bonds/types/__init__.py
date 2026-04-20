"""Bond-domain enums, identifiers, and rule objects.

This subpackage collects the stable type system used to interpret bond
reference data and pricing conventions. It includes identifier wrappers, quote
semantics, yield and settlement rules, stub handling, compounding, and product
classification enums.
"""

from __future__ import annotations

from .amortization import AmortizationEntry, AmortizationSchedule, AmortizationType
from .asw import ASWType
from .compounding import CompoundingKind, CompoundingMethod
from .ex_dividend import ExDividendRules
from .inflation import InflationIndexReference, InflationIndexType
from .identifiers import BondIdentifiers, Cusip, Figi, Isin, Sedol
from .options import PutEntry, PutSchedule, PutType
from .price_quote import PriceQuote, PriceQuoteConvention
from .rate_index import RateIndex
from .rating import CreditRating, RatingInfo
from .sector import Sector, SectorInfo
from .seniority import Seniority, SeniorityInfo
from fuggers_py._core.settlement_rules import SettlementRules
from .sofr_convention import SOFRConvention
from .stub_rules import StubPeriodRules, StubType
from fuggers_py._core.tenor import TenorUnit
from .yield_convention import (
    AccruedConvention,
    RoundingConvention,
    RoundingKind,
    YieldConvention,
)

__all__ = [
    # Identifiers / calendars
    "Isin",
    "Cusip",
    "Sedol",
    "Figi",
    "BondIdentifiers",
    "AmortizationEntry",
    "AmortizationSchedule",
    "AmortizationType",
    # Tenor
    "TenorUnit",
    # Quotes
    "PriceQuoteConvention",
    "PriceQuote",
    "RateIndex",
    "ASWType",
    "PutEntry",
    "PutSchedule",
    "PutType",
    # Yield conventions / rules
    "YieldConvention",
    "AccruedConvention",
    "RoundingKind",
    "RoundingConvention",
    # Compounding
    "CompoundingKind",
    "CompoundingMethod",
    # Settlement
    "SettlementRules",
    # Stubs / ex-div
    "StubType",
    "StubPeriodRules",
    "ExDividendRules",
    "SOFRConvention",
    "InflationIndexReference",
    "InflationIndexType",
    "CreditRating",
    "RatingInfo",
    "Sector",
    "SectorInfo",
    "Seniority",
    "SeniorityInfo",
]
