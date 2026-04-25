# API guide

The public API has one root package and eight first-layer domain packages.
Import shared language from `fuggers_py`. Import domain objects from the domain
package that owns them.

```python
from fuggers_py import Currency, Date, InstrumentId, Price
from fuggers_py.bonds import FixedBondBuilder
from fuggers_py.curves import CurveSpec, YieldCurve
from fuggers_py.portfolio import Portfolio
```

The root package is for shared words used across the library. It does not export
domain tools such as `BondPricer` or `YieldCurve`. Those stay under
`fuggers_py.bonds` and `fuggers_py.curves`.

## First-Layer Packages

- `curves`: built curve objects, curve identity, curve shape choices,
  calibration inputs, and calibration reports.
- `vol_surfaces`: volatility surface snapshots, points on those surfaces, and
  surface source interfaces.
- `bonds`: bond instruments, bond quotes, bond pricing, bond risk, bond
  spreads, bond yields, reference records, and YAS-style bond analytics.
- `rates`: swaps, basis swaps, FRAs, government bond futures, rates options,
  rate quotes, overnight fixing storage, and rates risk.
- `inflation`: CPI history, inflation index conventions, reference CPI,
  index-ratio helpers, inflation swaps, and inflation analytics.
- `credit`: CDS instruments, CDS quotes, CDS pricing, CDS risk, and bond-CDS
  basis analytics.
- `funding`: repo trades, repo quotes, haircut quotes, carry, implied repo,
  financing cost, and specialness helpers.
- `portfolio`: holdings, portfolio containers, analytics, benchmark comparison,
  contribution, bucketing, ETF workflows, liquidity, and stress.

## Root Exports

The root exports the first-layer packages plus shared types and conventions.

| Export | What it represents | Notes |
| --- | --- | --- |
| `__version__` | Installed package version. | String. |
| `curves`, `vol_surfaces`, `bonds`, `rates`, `inflation`, `credit`, `funding`, `portfolio` | Public first-layer packages. | Use these package names for domain imports. |
| `Date` | Library date value. | Use for valuation dates, settlement dates, maturity dates, and fixing dates. |
| `YearMonth` | Calendar month value. | Use for monthly CPI observations and futures delivery months. |
| `Currency` | Currency code. | Common examples are `Currency.USD`, `Currency.EUR`, and `Currency.GBP`. |
| `Frequency` | Payment or coupon frequency. | Used by schedules, bonds, swaps, and CDS premium legs. |
| `Compounding` | How a rate compounds. | Used by yield and breakeven helpers. |
| `Price` | Typed price value. | Prices are usually percent-of-par unless a function says it needs a cash amount. |
| `Yield` | Typed yield value. | Raw yield inputs are decimals, so `0.05` means 5%. |
| `Spread` | Typed spread value. | Raw spread inputs are decimals, so `0.001` means 10 basis points. |
| `InstrumentId` | Identifier for one instrument. | Used by quotes, trades, reference records, and holdings. |
| `CurveId` | Identifier for one curve. | Used when several curves are stored or passed together. |
| `PortfolioId` | Identifier for one portfolio. | Used by portfolio containers and outputs. |
| `Tenor` | Term such as `3M`, `5Y`, or `30Y`. | Use `Tenor.parse("5Y")` for string input. |
| `DayCountConvention` | Rule for turning dates into year fractions. | Used by cash-flow, yield, swap, repo, and CDS calculations. |
| `BusinessDayConvention` | Rule for moving dates that fall on non-business days. | Used by schedules and settlement rules. |
| `CalendarId` | Calendar name. | Identifies which business-day calendar a schedule or settlement rule uses. |
| `SettlementAdjustment` | Settlement date adjustment rule. | Used by settlement and schedule helpers. |
| `YieldCalculationRules` | Bond yield convention bundle. | Use presets such as `YieldCalculationRules.us_treasury()`. |
| `BondType`, `IssuerType` | Bond classification enums. | Also available from `fuggers_py.bonds`. |
| `PayReceive` | Direction of a fixed leg, floating leg, or swap side. | Values describe whether the holder pays or receives that leg. |
| `OptionType` | Call or put option direction. | Used by bond options and rates options. |
| `USD_CPI_U_NSA` | Built-in US CPI-U NSA inflation convention. | Also available from `fuggers_py.inflation`. |
| `IndexConventions`, `OvernightCompounding` | Floating-rate and overnight index conventions. | Also available from `fuggers_py.rates`. |

## Input And Output Conventions

- Dates are `Date` values unless a loader reads text from disk.
- Rates, yields, spreads, recovery rates, haircuts, and volatilities are raw
  decimals unless the symbol name ends in `_bps` or `_pct`.
- A raw decimal rate of `0.05` means 5%.
- One basis point is `0.0001`.
- Prices are usually percent-of-par. A price of `99.5` means 99.5% of face.
- Cash amounts are currency-unit decimals.
- Quote records usually contain `instrument_id`, optional `as_of`, optional
  `source`, and optional `bid`, `ask`, and `mid`.

## Boundary Rules

- Use first-layer package imports in user code.
- Do not import from package roots that start with `_`.
- `portfolio` may combine objects from the other public packages.
- Other public packages should not depend on `portfolio`.
- Curve objects live in `curves`; quoted instruments and quote records live in
  the package that owns the instrument.
- Volatility surface records live in `vol_surfaces`; option products and
  pricers live with the domain that owns those products.

If you are new to the repo, read [Project Status](../STATUS.md) first. The API
surface is broad and usable, but the project is still pre-`1.0`.
Implementation-only modules are documented in
[Developer internal modules](../dev/internal_modules.md), not in this API guide.

```{toctree}
:maxdepth: 1

curves
vol_surfaces
bonds
rates
inflation
credit
funding
portfolio
```
