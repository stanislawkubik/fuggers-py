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

- Use `dv01` for the main one-basis-point risk field in public bond, rates,
  portfolio, and runtime outputs.
- Some older or domain-specific paths still expose `pv01`. Runtime output
  records backfill `pv01` from `dv01`, or `dv01` from `pv01`, and reject the
  record if both are supplied with different values.
- The rates risk module defines `pv01()` as the implementation function, then
  aliases `dv01 = pv01` and `bpv = pv01`.
- Credit and inflation still use `pv01` names where that is the normal product
  language, such as CDS risky PV01 and inflation-swap PV01.
- Positive DV01 means the value rises when rates, yields, or spreads fall by
  one basis point.

## Methodology note

The code uses the same sign convention, but not every product computes the
number the same way.

For bonds, the direct duration formula is:

```python
dv01 = modified_duration * (dirty_price / 100) * face * Decimal("0.0001")
```

For bumped bond prices, the finite-difference formula is:

```python
dv01 = (price_down - price_up) / Decimal(2)
```

`price_down` means the price after the yield, rate, or spread is moved down.
`price_up` means the price after it is moved up. If the instrument has normal
positive duration, `price_down` is larger than `price_up`, so DV01 is positive.

For rates products, the same finite-difference idea is applied to PV:

```python
pv01 = (pv_with_rates_down - pv_with_rates_up) / Decimal(2)
dv01 = pv01
bpv = pv01
```

This is why the names stay aligned even though the calculation path differs by
product.
