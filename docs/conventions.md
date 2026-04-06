# Conventions

This page defines the shared public conventions used across `fuggers-py`.

## Bond prices

- Bond `clean_price` and `dirty_price` stay in percent-of-par where the API
  already uses percent-of-par.
- Coupon-per-price helpers that take bond prices assume the same per-100-face
  convention.

## Unsuffixed yields, rates, and spreads

- Shared/public unsuffixed yields, rates, and spreads use raw decimal units.
- Example: `0.05` means 5%, `0.0025` means 25 bp.
- Shared calc outputs follow the same rule for fields such as
  `yield_to_maturity`, `current_yield`, `z_spread`, `g_spread`, `i_spread`,
  `discount_margin`, and `asset_swap_spread`.

## Display helpers

- Use `_pct` helpers for quoted percentage display values.
- Use `_bps` helpers for basis-point display values.
- YAS is display-oriented, so YAS keeps quoted percentages and basis points in
  its output fields.

## DV01, PV01, and BPV

- `dv01` is the canonical first-order risk name across the library.
- `pv01` remains a backward-compatible alias to `dv01`.
- `bpv` remains a backward-compatible alias in the rates namespace.
- Sign convention is signed and uniform: the value is positive when PV rises as
  rates or yields fall by 1 bp.

## Methodology note

- Bond `dv01` may be computed from a bond-yield or YTM-based bump path,
  depending on the bond analytics being used.
- Rates `dv01` is typically computed from a parallel curve bump.
- The naming and sign convention stay aligned even when the underlying bump
  methodology differs.
