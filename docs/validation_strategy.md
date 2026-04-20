# Validation Strategy

Validation is split into two layers.

## Workflow gates

We use two hook-based workflows for changes that can break the library in a broad way.

- `$add-feature` uses its own spec-first validator and reviewer flow.
- The public API refactor uses `tools/validate_public_api_refactor.py`.

The public API refactor gate is intentionally small and fast.

- Start it with `python tools/validate_public_api_refactor.py init`.
- While it is active, the hooks inject the workflow on every prompt.
- It treats the library move as a hard rewrite, not a backward-compatibility migration.
- It checks that user-facing imports stay one layer deep.
- It rejects compatibility wrappers and old public re-export shims in legacy namespaces.
- It checks that moved code is not left behind in both the old and new location.
- It requires a read-only `public_api_reviewer` review artifact before a change set can be sealed.
- It uses the current dirty tree as the starting baseline, so it should start before the refactor work for that change set begins.
- End the active mode with `python tools/validate_public_api_refactor.py deactivate` or `clear`.

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
