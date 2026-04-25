# Validation Strategy

Validation is split into two layers.

## Human-runnable gates

The validation commands are the source of truth. Hooks may call the same
commands, but hooks are optional wrappers, not the main validation surface. Every
developer can run the checks from a normal shell:

```bash
python tools/validate_docs_coverage.py
python tools/validate_api_cleanliness.py
python tools/validate_public_api_surface.py
python tools/validate_public_api_surface.py --check-contract-permission
python -m pytest -q tests/contracts/tooling
```

These gates enforce the normal source and public API rules:

- keep public imports one layer deep under the current first-layer modules
- do not add compatibility aliases, forwarding modules, or dynamic import
  wrappers to keep old paths alive
- keep public exports explicit in literal `__all__` lists
- update matching API tests and docs when public exports change
- update the public API surface contract only when the user explicitly asks for
  that change

The tooling also handles explicit workflow or API-change intent:

- `$add-feature` injects the spec-first feature workflow.
- Requests such as `update public API surface` allow one deliberate update to
  `specs/public_api_surface.json`.

## Optional local hooks

Local hooks are optional convenience wrappers around the commands above. They
can be used in the same local automation path as before, but they are not a
separate source of rules.

The wrapper entry points are:

```bash
python tools/repo_hooks.py user-prompt-hook
python tools/repo_hooks.py stop-hook
```

At the start of a hook-tracked turn, the wrapper records the current dirty tree.
The stop hook then gates only files whose content changed after that turn
started. If a file was already dirty or untracked at the start, a later content
edit is treated as a modification, not as a new add. This keeps old dirty source
files from turning a later docs or example edit into a source validation run.

The stop hook runs these gates:

- `tools/validate_add_feature.py stop-hook` blocks unfinished `$add-feature`
  work.
- For files changed in the current hook-tracked turn,
  `tools/validate_docs_coverage.py` checks lightweight docs expectations. For
  example, a new example notebook requires `examples/README.md`, and
  hook/tooling edits require this validation strategy page or the add-feature
  workflow README.
- For `src/` files changed in the current hook-tracked turn,
  `tools/validate_api_cleanliness.py` rejects old API paths, compatibility
  wrappers, `sys.modules` aliases, and unclear public imports.
- When a public `__init__.py` or `specs/public_api_surface.json` changes in the
  current hook-tracked turn, `tools/validate_public_api_surface.py` checks that
  the public export lists still match `specs/public_api_surface.json`.
- When `specs/public_api_surface.json` changes in the current hook-tracked turn,
  `tools/validate_public_api_surface.py --check-contract-permission` blocks the
  contract update unless the user explicitly asked for one.

Docs, examples, tests, and notebooks do not run the source API gates unless the
same change set also changes `src/` or the public API surface contract.

The hook wrapper behavior is covered by
`tests/contracts/tooling/test_repo_hooks_router.py`. The validators themselves
are covered by the other `tests/contracts/tooling/test_*_validator.py` files.

The same structural gates run in the CI quality job:

```bash
python tools/validate_api_cleanliness.py
python tools/validate_public_api_surface.py
python tools/validate_public_api_surface.py --check-contract-permission
python tools/validate_docs_coverage.py
```

On pull requests, CI fetches the target branch and passes `--base-ref
origin/<target-branch>` to the diff-based gates. This makes those gates compare
the pull request changes against the branch being merged into. Local no-argument
runs still compare against the current working tree.

## Public API contract

The public API contract lives in:

```text
specs/public_api_surface.json
```

It records the names exposed by the first-layer public modules:

- `fuggers_py`
- `fuggers_py.bonds`
- `fuggers_py.credit`
- `fuggers_py.curves`
- `fuggers_py.funding`
- `fuggers_py.inflation`
- `fuggers_py.portfolio`
- `fuggers_py.rates`
- `fuggers_py.vol_surfaces`

Update this file only when the user explicitly asks for a public API surface
change. Use:

```bash
python tools/update_public_api_surface.py
```

If the public API changed, also update the matching page under `docs/api/` and
the matching public API contract tests.

## Add-feature workflow

`$add-feature` uses its own spec-first validator and reviewer flow. Start it
with:

```bash
python tools/validate_add_feature.py init --slug <feature-slug>
```

Finish it with:

```bash
python tools/validate_add_feature.py validate --mark-passed
```

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
