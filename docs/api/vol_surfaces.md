# `fuggers_py.vol_surfaces`

Public home for volatility surface records and surface source interfaces.

Use one-layer imports from `fuggers_py.vol_surfaces`.

```python
from fuggers_py.vol_surfaces import (
    InMemoryVolatilitySource,
    VolPoint,
    VolQuoteType,
    VolSurfaceSourceType,
    VolSurfaceType,
    VolatilitySource,
    VolatilitySurface,
)
```

## What This Package Owns

`vol_surfaces` owns simple volatility surface records and source interfaces. A
surface is one set of quoted values for one market object, such as a swaption
surface or cap/floor surface.

This package does not own option contracts, option pricing, calibration, or data
downloads. Other modules can read these records and decide how to price from
them.

Public exports:

| Export | What it is |
| --- | --- |
| `VolPoint` | One quoted point on a surface. |
| `VolatilitySurface` | One surface snapshot with an id, type, points, and source details. |
| `VolQuoteType` | The meaning of the number stored on a point. |
| `VolSurfaceType` | The market category for the surface. |
| `VolSurfaceSourceType` | Where the surface came from. |
| `VolatilitySource` | A read interface with `get_volatility_surface(surface_id)`. |
| `InMemoryVolatilitySource` | A small in-memory implementation of `VolatilitySource`. |

## Basic Example

```python
from datetime import date
from decimal import Decimal

from fuggers_py import YearMonth
from fuggers_py.vol_surfaces import (
    InMemoryVolatilitySource,
    VolPoint,
    VolQuoteType,
    VolSurfaceSourceType,
    VolSurfaceType,
    VolatilitySurface,
)

normal_point = VolPoint(
    expiry=YearMonth(2027, 1),
    tenor=YearMonth(2031, 1),
    strike=Decimal("0.04"),
    volatility=Decimal("0.21"),
    quote_type=VolQuoteType.NORMAL,
)

lognormal_point = VolPoint(
    expiry=YearMonth(2026, 7),
    volatility=Decimal("0.18"),
    quote_type=VolQuoteType.LOGNORMAL,
)

surface = VolatilitySurface(
    surface_id="USD_SWAPTION",
    surface_type=VolSurfaceType.SWAPTION,
    as_of=date(2026, 4, 17),
    points=(normal_point, lognormal_point),
    source=" close run ",
    source_type=VolSurfaceSourceType.CLOSE,
)

source = InMemoryVolatilitySource([surface])
loaded = source.get_volatility_surface("USD_SWAPTION")

print(loaded.surface_id)
print(loaded.source)
print([point.expiry for point in loaded.points])
```

Output:

```text
USD_SWAPTION
close run
[YearMonth(year=2026, month=7), YearMonth(year=2027, month=1)]
```

The output shows two constructor behaviors:

- `surface_id` is parsed from a string into the package id type.
- `source` is stripped, and `points` are stored in sorted order.

## `VolPoint`

`VolPoint` represents one quoted point on a volatility surface. Use it for one
expiry, and optionally one tenor, strike, or delta.

Fields:

| Field | Meaning |
| --- | --- |
| `expiry` | Expiry as a `YearMonth`. The constructor parses it with `YearMonth.parse`. |
| `volatility` | The stored quote number. The constructor converts it to `Decimal`. |
| `strike` | Optional strike. The constructor converts it to `Decimal` when present. |
| `tenor` | Optional underlying tenor as a `YearMonth`. The constructor parses it with `YearMonth.parse` when present. |
| `delta` | Optional delta bucket. The constructor converts it to `Decimal` when present. |
| `quote_type` | A `VolQuoteType`. Default is `VolQuoteType.LOGNORMAL`. |

Implementation behavior:

- `expiry` and `tenor` accept the same inputs as `YearMonth.parse`.
- `volatility`, `strike`, and `delta` are converted to `Decimal`.
- `quote_type` is not converted by this class. Pass a `VolQuoteType` value.
- The class is frozen. Read fields after construction instead of changing them.
- The class does not check whether a point has a strike, tenor, delta, or a
  specific combination of them. Keep the shape consistent within each surface.
- The class does not define a delta sign rule. Store delta in the convention your
  data source uses, and document that convention near the data.

Useful public fields:

```python
from fuggers_py.vol_surfaces import VolPoint, VolQuoteType

point = VolPoint(
    expiry="2027-01",
    tenor="2031-01",
    strike="0.04",
    volatility="0.21",
    delta="0.25",
    quote_type=VolQuoteType.NORMAL,
)

print(point.expiry)
print(point.tenor)
print(point.strike)
print(point.volatility)
print(point.delta)
print(point.quote_type)
```

Output:

```text
2027-01
2031-01
0.04
0.21
0.25
VolQuoteType.NORMAL
```

## `VolatilitySurface`

`VolatilitySurface` represents one snapshot of points for one surface id. Use it
when you want to pass a complete surface between data loading code, research
code, and pricing code.

Fields:

| Field | Meaning |
| --- | --- |
| `surface_id` | The surface id. The constructor parses it with `VolSurfaceId.parse`. |
| `surface_type` | A `VolSurfaceType`. Pass the enum value. |
| `as_of` | Optional business date for the snapshot. |
| `timestamp` | Optional exact timestamp for the snapshot. |
| `points` | Surface points. Stored as a sorted tuple. |
| `source` | Optional source name. Whitespace is stripped when present. |
| `source_type` | Optional `VolSurfaceSourceType`. Strings such as `"CLOSE"` are accepted. |

Implementation behavior:

- `surface_id` accepts the same inputs as `VolSurfaceId.parse`.
- `points` is converted to a tuple and sorted by expiry year, expiry month, and
  quote number.
- `source` is stripped with `str.strip()`.
- `source_type` is converted to `VolSurfaceSourceType` when present.
- `surface_type`, `as_of`, and `timestamp` are stored as passed.
- The class is frozen. Build a new surface if you need different fields.

Example showing normalization and sorting:

```python
from datetime import date

from fuggers_py.vol_surfaces import (
    VolPoint,
    VolQuoteType,
    VolSurfaceType,
    VolatilitySurface,
)

later = VolPoint(expiry="2028-01", volatility="0.24", quote_type=VolQuoteType.LOGNORMAL)
earlier = VolPoint(expiry="2027-01", volatility="0.21", quote_type=VolQuoteType.LOGNORMAL)

surface = VolatilitySurface(
    surface_id="USD_SWAPTION",
    surface_type=VolSurfaceType.SWAPTION,
    as_of=date(2026, 4, 17),
    points=[later, earlier],
    source=" internal close ",
    source_type="CLOSE",
)

print(surface.surface_id)
print(surface.source)
print(surface.source_type)
print([(point.expiry.year, point.expiry.month) for point in surface.points])
```

Output:

```text
USD_SWAPTION
internal close
VolSurfaceSourceType.CLOSE
[(2027, 1), (2028, 1)]
```

## `VolQuoteType`

`VolQuoteType` says what the number on `VolPoint.volatility` means. The enum is
a label only. This package stores the value; it does not convert it or price
from it.

Values:

| Value | Meaning |
| --- | --- |
| `LOGNORMAL` | A lognormal volatility quote. `Decimal("0.20")` means 20%. |
| `NORMAL` | A normal volatility quote. Use the unit convention of the source data. |
| `PRICE` | A price quote stored in the `volatility` field. |
| `SPREAD` | A spread quote stored in the `volatility` field. |

Example:

```python
from fuggers_py.vol_surfaces import VolPoint, VolQuoteType

points = [
    VolPoint(expiry="2027-01", volatility="0.20", quote_type=VolQuoteType.LOGNORMAL),
    VolPoint(expiry="2027-01", volatility="0.0075", quote_type=VolQuoteType.NORMAL),
    VolPoint(expiry="2027-01", volatility="1.85", quote_type=VolQuoteType.PRICE),
]

for point in points:
    print(point.quote_type.value, point.volatility)
```

Output:

```text
LOGNORMAL 0.20
NORMAL 0.0075
PRICE 1.85
```

## `VolSurfaceType`

`VolSurfaceType` identifies the market category for a surface. Use it so
consumers can choose the right interpretation for the same shape of data.

Values:

| Value | Meaning |
| --- | --- |
| `SWAPTION` | Swaption volatility surface. |
| `CAP_FLOOR` | Cap and floor volatility surface. |
| `FX_OPTION` | Foreign exchange option volatility surface. |
| `BOND_OPTION` | Bond option volatility surface. |
| `ETF_OPTION` | ETF option volatility surface. |

Example:

```python
from fuggers_py.vol_surfaces import VolSurfaceType

surface_type = VolSurfaceType.SWAPTION
print(surface_type.value)
```

Output:

```text
SWAPTION
```

## `VolSurfaceSourceType`

`VolSurfaceSourceType` identifies where the surface came from. Use it to separate
live data, close data, reference data, model output, and manual data.

Values:

| Value | Meaning |
| --- | --- |
| `LIVE` | Intraday or live source. |
| `CLOSE` | Official or internal close source. |
| `REFERENCE` | Reference data source. |
| `MODEL` | Model-generated surface. |
| `MANUAL` | Manually entered surface. |

Example:

```python
from fuggers_py.vol_surfaces import VolSurfaceSourceType

source_type = VolSurfaceSourceType("CLOSE")
print(source_type)
print(source_type.value)
```

Output:

```text
VolSurfaceSourceType.CLOSE
CLOSE
```

## `VolatilitySource`

`VolatilitySource` is the read interface for surface providers. An interface is
the small set of methods another object must provide. Here there is one method:
`get_volatility_surface(surface_id)`.

Method:

| Method | Behavior |
| --- | --- |
| `get_volatility_surface(surface_id)` | Return the matching `VolatilitySurface`, or `None` when the id is missing. |

The public protocol only supports lookup by surface id. It does not define
lookup by date, currency, expiry, tenor, or surface type.

Example function that accepts any compatible source:

```python
from fuggers_py.vol_surfaces import VolatilitySource


def require_surface(source: VolatilitySource, surface_id: str):
    surface = source.get_volatility_surface(surface_id)
    if surface is None:
        raise ValueError(f"Missing volatility surface: {surface_id}")
    return surface
```

## `InMemoryVolatilitySource`

`InMemoryVolatilitySource` stores surfaces in a Python dictionary. Use it in
examples, tests, and research code when the surfaces are already in memory.

Public field:

| Field | Meaning |
| --- | --- |
| `surfaces` | Dictionary keyed by normalized surface id. Values are `VolatilitySurface` objects. |

Methods:

| Method | Behavior |
| --- | --- |
| `InMemoryVolatilitySource(surfaces=None)` | Builds an empty source, then adds each supplied surface. |
| `add_surface(surface)` | Stores or replaces a surface by `surface.surface_id`, then returns `self`. |
| `get_volatility_surface(surface_id)` | Parses string ids, then returns the surface or `None`. |

Example:

```python
from datetime import date

from fuggers_py.vol_surfaces import (
    InMemoryVolatilitySource,
    VolPoint,
    VolSurfaceType,
    VolatilitySurface,
)

surface = VolatilitySurface(
    surface_id="USD_SWAPTION",
    surface_type=VolSurfaceType.SWAPTION,
    as_of=date(2026, 4, 17),
    points=(VolPoint(expiry="2027-01", volatility="0.20"),),
)

source = InMemoryVolatilitySource()
same_source = source.add_surface(surface)

loaded = source.get_volatility_surface("USD_SWAPTION")
missing = source.get_volatility_surface("EUR_SWAPTION")

print(same_source is source)
print(loaded is surface)
print(missing is None)
print(list(source.surfaces))
```

Output:

```text
True
True
True
[VolSurfaceId(value='USD_SWAPTION')]
```

## Boundaries

- Rates options such as swaptions, caps, floors, and futures options live in
  `fuggers_py.rates`.
- Bond options and callable-bond option models live in `fuggers_py.bonds`.
- Curve objects live in `fuggers_py.curves`.
- Full smile, cube, and calibration workflows are not part of this public
  surface yet.

```{eval-rst}
.. automodule:: fuggers_py.vol_surfaces
   :members:
   :member-order: bysource
```
