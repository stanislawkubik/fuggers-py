# Docstring Standard

This page defines the house style for docstrings in `fuggers-py`.

The goal is simple: generated API docs should be complete enough that a reader
can use the public API correctly without opening the source. A good docstring
explains the contract and the financial interpretation. It does not narrate the
implementation.

## Format

- Use NumPy-style docstrings.
- Write in plain English.
- Keep the summary line short and concrete.
- Use the minimum set of sections that makes the contract complete.
- Prefer a short, precise docstring over a long one full of filler.

`docs/conf.py` is already configured for NumPy-style parsing through Sphinx
Napoleon, so the standard should match the docs toolchain.

## Core rule

For public APIs, the docstring should answer four questions:

1. What does this object or function do?
2. How should the result be interpreted?
3. What do the inputs mean?
4. What comes back, in what units or conventions?

In this library, "interpretation" matters as much as the signature. A
docstring is often incomplete if it does not explain units, sign conventions,
raw-decimal versus percent-of-par quoting, adjusted versus unadjusted dates, or
calendar and accrual assumptions.

## What To Document

### Public modules

Module docstrings should state:

- the scope of the module
- the kinds of objects or workflows it contains
- shared conventions that apply across the module

Use the module docstring to explain the domain role of the file, not to list
every symbol in it.

### Public classes and dataclasses

Class docstrings should state:

- what the object represents
- the main invariants or conventions carried by the object
- the meaning of important constructor parameters
- key attributes when they are not obvious from the field names

For simple dataclasses, `Parameters` is often enough. Add `Attributes` only when
it helps the generated docs read better.

### Public functions and methods

Function and method docstrings should usually contain:

- a one-line summary
- a short methodology paragraph when the "how" changes interpretation
- `Parameters`
- `Returns`
- `Raises` for meaningful failure modes
- `Notes` when units, sign rules, accrual rules, or side effects matter
- `Examples` only when the API is easy to misuse or benefits from a concrete use

Do not add sections mechanically. If a section adds no information, omit it.

### Small public helpers

A one-line docstring is enough for:

- trivial properties
- obvious enum helpers
- exception subclasses
- methods whose name and type signature already tell the full story

Example:

```python
def sign(self) -> Decimal:
    """Return ``-1`` for pay legs and ``+1`` for receive legs."""
```

## Section Guidance

### Summary line

The first line should tell the reader exactly what the object does.

Good:

- "Return accrual periods for the schedule."
- "Plain fixed-for-floating interest-rate swap."
- "Return the instrument DV01 from a parallel rate bump."

Avoid vague summaries such as:

- "Utility helper for calculations."
- "Class representing bond-related functionality."
- "Comprehensive engine for robust pricing workflows."

### Methodology paragraph

Use a short paragraph after the summary only when the approach affects how the
output should be read.

Good reasons to include it:

- the function bumps a rate rather than a yield
- accrual uses unadjusted dates while payment uses adjusted dates
- a measure is quoted in percent-of-par but stored internally in raw decimals
- the routine mutates state, publishes events, or caches results

Do not explain line-by-line implementation details.

### Parameters

For each important parameter, document:

- the business meaning
- units and quoting conventions
- accepted aliases or normalization rules
- defaults when they materially change behavior

Do not restate the annotation unless the type itself needs interpretation.

Good:

```text
Parameters
----------
bump_size:
    Parallel bump in raw decimal units. ``0.0001`` means 1 bp.
```

Less useful:

```text
Parameters
----------
bump_size:
    Decimal value.
```

### Returns

State:

- what is returned
- the units
- the sign convention when relevant
- ordering or shape when returning sequences or tuples

Examples:

- "DV01 in currency units."
- "Tuple of accrual periods ordered from start date to end date."
- "Clean price in percent of par."

### Raises

Document exceptions that matter to users of the API:

- invalid conventions or unsupported aliases
- missing market inputs
- out-of-range interpolation when extrapolation is disallowed
- scheduling or routing failures in calc-layer code

Do not list every generic exception path.

### Notes

Use `Notes` for information that is important but does not belong to a single
parameter or return value.

Typical examples in this repo:

- raw decimal conventions for rates and spreads
- percent-of-par conventions for prices
- signed DV01/PV01 behavior
- adjusted versus unadjusted date treatment
- calendar or settlement assumptions

When a library-wide rule already exists in [conventions](conventions.md), keep
the docstring short and align with that rule instead of rewriting the full
policy each time.

### Examples

Add examples when:

- the API has a non-obvious calling pattern
- a common mistake is easy to make
- the output format is easier to understand from a short snippet

Skip examples for obvious helpers.

## Style Rules

- Prefer simple words over impressive words.
- Use direct verbs: "Return", "Compute", "Generate", "Normalize", "Parse".
- Explain the domain effect, not the internal plumbing.
- Do not use marketing language such as "powerful", "robust", or
  "comprehensive".
- Do not use jargon when plain language is enough.
- Do not over-repeat type information already present in annotations.
- Keep private helper docstrings short unless the behavior is subtle and reused.

## Repo-Specific Requirements

When documenting public APIs in `fuggers-py`, explicitly mention conventions
whenever they affect correct usage:

- raw decimal rates, yields, spreads, and accrual factors
- percent-of-par price conventions
- basis-point interpretation of bumps
- sign conventions for risk measures
- business-day adjustment rules
- adjusted versus unadjusted schedule dates
- currencies, notionals, and quote sides where relevant

These are not optional details. They are part of the API contract.

## Recommended Templates

### Function or method

```python
def some_function(arg1: Type1, arg2: Type2 = default) -> ReturnType:
    """Return ...

    Short methodology note only when it affects interpretation.

    Parameters
    ----------
    arg1:
        Meaning of the input, including units or conventions.
    arg2:
        Meaning of the optional input and what the default implies.

    Returns
    -------
    ReturnType
        Meaning of the returned value, including units or conventions.

    Raises
    ------
    SomeError
        When the input or state violates the public contract.

    Notes
    -----
    Any important repo-specific convention that does not fit elsewhere.
    """
```

### Dataclass or value object

```python
@dataclass(frozen=True, slots=True)
class SomeSpec:
    """Description of the domain object.

    Parameters
    ----------
    field_one:
        Business meaning and conventions.
    field_two:
        Business meaning and conventions.
    """
```

## Reference Example

This is the target level of detail for an important public measure:

```python
def dv01(
    instrument: Bond,
    yield_to_maturity: Decimal,
    bump_size: Decimal = Decimal("0.0001"),
) -> Decimal:
    """Return the instrument DV01 from a parallel yield bump.

    The instrument is repriced at the base yield and at a bumped yield. The
    result follows the library sign convention: DV01 is positive when PV rises as
    yields fall.

    Parameters
    ----------
    instrument:
        Instrument to reprice.
    yield_to_maturity:
        Base yield used for valuation.
    bump_size:
        Parallel yield bump in raw decimal units. ``0.0001`` means 1 bp.

    Returns
    -------
    Decimal
        DV01 in currency units.
    """
```

## Practical Bar

Use this checklist before calling a public docstring done:

- Can a reader understand the business meaning from the summary alone?
- Does the docstring explain units and conventions where needed?
- Would a user know how to call the API correctly without reading the source?
- Did we avoid filler and implementation trivia?

If the answer to all four is yes, the docstring is probably at the right level.
