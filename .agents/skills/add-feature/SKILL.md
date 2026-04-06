---
name: add-feature
description: Mandatory workflow for `$add-feature <feature request>` in this repo. Use it when the user wants a new library feature or behavior change implemented through a spec-first process with reviewer agents, tagged pytest coverage, and validator-gated completion.
---

# Add Feature

Use this skill only for the explicit trigger `$add-feature <feature request>` or when the user asks to run the repo's add-feature workflow.

This workflow is mandatory in `fuggers-py`.

## Goal

Reduce implementer bias in tests for fixed-income features.

Do that by forcing:
- a machine-readable feature spec before implementation
- independent read-only review before and after coding
- pytest tagging for feature-owned tests
- validator-gated completion

## Required order

1. Derive a short kebab-case slug from the request.
2. Start the workflow immediately:

```bash
python tools/validate_add_feature.py init --slug <feature-slug>
```

3. Fill `.tmp/add-feature/specs/<feature-slug>.json` before code edits.
4. Ask the read-only reviewer agents for review and write their outputs to the temporary workflow area:
   - `.tmp/add-feature/reviews/<feature-slug>.fi_api_reviewer.md`
   - `.tmp/add-feature/reviews/<feature-slug>.fi_finance_reviewer.md`
   These two reviews happen before implementation.
5. Implement the feature.
6. Run the diff reviewer after implementation and update:
   - `.tmp/add-feature/reviews/<feature-slug>.fi_diff_reviewer.md`
7. Add pytest markers to every feature-owned test:

```python
import pytest

@pytest.mark.feature_slug("<feature-slug>")
@pytest.mark.feature_category("<category>")
def test_example() -> None:
    ...
```

8. Keep `feature_category` aligned with the repo tree:
   - `unit` -> `tests/unit/`
   - `validation` -> `tests/integration/validation/`
   - `properties` -> `tests/integration/properties/`
   - `workflow` -> `tests/integration/workflows/`
   - `api_contract` -> `tests/contracts/api/`
   - `architecture_contract` -> `tests/contracts/architecture/`
   - `docs_smoke` -> `tests/contracts/docs/`
   - `examples_smoke` -> `tests/integration/examples/`

9. For fixed-income features, default the minimum required categories to:
   - `unit`
   - `validation`
   - `properties`

10. Add stronger categories when the feature shape requires them:
   - add `api_contract` when `public_api.new_symbols` or `public_api.changed_symbols` is non-empty
   - add `workflow` when the implementation changes `src/fuggers_py/calc/` or `src/fuggers_py/portfolio/`
   - add `docs_smoke` when docs or `README.md` change, or when docs files are listed in `public_api.docs_examples_to_update`
   - add `examples_smoke` when examples change, or when example files are listed in `public_api.docs_examples_to_update`
11. Do not finish until this passes:

```bash
python tools/validate_add_feature.py validate --mark-passed
```

Use ordinary `validate` runs as a fast checkpoint during work.
Use `validate --full` if you want the heavyweight repo-wide gate without closing the workflow.

12. If the workflow becomes stale or the task is abandoned, clear the active state explicitly:

```bash
python tools/validate_add_feature.py clear --slug <feature-slug>
```

## Feature spec requirements

The spec must include, at minimum:
- `summary`
- `public_api`
- `formulas_or_rules`
- `conventions`
- `accepted_inputs`
- `rejected_inputs`
- `edge_cases`
- `invariants`
- `numerical_tolerance`
- `required_test_categories`

Keep the spec concrete and machine-readable.

## Reviewer usage

Use these custom read-only agents from `.codex/agents/`:
- `fi_api_reviewer` before implementation
- `fi_finance_reviewer` before implementation
- `fi_diff_reviewer` after implementation exists

Write their outputs into the temporary review files and make sure each file says `Status: complete`.
The validator also expects structured sections such as findings, missing tests, and a verdict.

## Validation

The validator will fail if:
- the feature spec file is missing or incomplete
- reviewer output files are missing or still pending
- the feature spec shape is too vague to be machine-checked
- required test categories are missing
- changed behavior has no changed feature-owned tests
- changed feature-owned tests do not cover every required category
- conditional categories required by public API, workflow, docs, or examples are missing
- the repo validation commands fail

`validate` runs the fast checkpoint command set for in-progress work.
`validate --full` and `validate --mark-passed` run the heavyweight repo-wide command bundle.

The Stop hook uses `.tmp/add-feature/.state.json` and blocks completion until the workflow is marked passed.
`validate --mark-passed` and `clear` automatically delete the temporary spec, temporary review files, and workflow state.
The UserPromptSubmit hook also injects workflow instructions whenever the user uses `$add-feature`.
