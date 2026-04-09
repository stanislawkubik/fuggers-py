# Validation Strategy

Validation is split into two layers.

## Deterministic validation suite

`tests/integration/validation/` contains scenario fixtures for:

- bond pricing and accrued-interest edge cases
- callable and floating-rate analytics
- portfolio analytics and ETF workflows
- engine scheduler and reactive flows

## External-reference corpus

`tests/integration/validation/test_validation_corpus.py` consumes `tests/fixtures/golden/validation_corpus.json`.

- The corpus is local and deterministic.
- It records the upstream repository, branch, commit, and generation date in fixture metadata.
- It is intentionally small and focused on high-value pricing and portfolio workflows.
- Accepted divergences are documented inline in the fixture when the Python implementation deliberately optimizes for internal coherence rather than exact path-by-path reproduction.

## Tolerances

- Tight scalar tolerances are used for deterministic bond cases.
- Exact or near-exact `Decimal` tolerances are used for many portfolio aggregates.
- Wider explicit tolerances are reserved for model-driven workflows such as callable OAS and floating-rate discount-margin checks.
