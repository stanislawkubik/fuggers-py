"""Public root for the :mod:`fuggers_py` fixed-income library.

The root package exposes two things:

1. the first-layer public modules such as ``curves`` and ``bonds``
2. the shared language used across those modules

The shared language stays small and deliberate. Domain objects such as
``BondPricer`` or ``YieldCurve`` belong in their domain modules, not here.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as distribution_version

from . import bonds, credit, curves, funding, inflation, portfolio, rates, vol_surfaces
from ._core import (
    BusinessDayConvention,
    CalendarId,
    Compounding,
    Currency,
    CurveId,
    Date,
    DayCountConvention,
    Frequency,
    InstrumentId,
    OptionType,
    PayReceive,
    PortfolioId,
    Price,
    SettlementAdjustment,
    Spread,
    Tenor,
    YearMonth,
    Yield,
    YieldCalculationRules,
)
from .bonds.types import BondType, IssuerType
from .inflation import USD_CPI_U_NSA
from .rates import IndexConventions, OvernightCompounding

try:
    from ._version import version as __version__
except ImportError:
    try:
        __version__ = distribution_version("fuggers-py")
    except PackageNotFoundError:
        __version__ = "0.0.dev0"

__all__ = [
    "__version__",
    "curves",
    "vol_surfaces",
    "bonds",
    "rates",
    "inflation",
    "credit",
    "funding",
    "portfolio",
    "Date",
    "Currency",
    "Frequency",
    "Compounding",
    "Price",
    "Yield",
    "Spread",
    "InstrumentId",
    "CurveId",
    "PortfolioId",
    "YearMonth",
    "Tenor",
    "DayCountConvention",
    "BusinessDayConvention",
    "CalendarId",
    "SettlementAdjustment",
    "YieldCalculationRules",
    "BondType",
    "IssuerType",
    "PayReceive",
    "OptionType",
    "USD_CPI_U_NSA",
    "IndexConventions",
    "OvernightCompounding",
]
