# Add-Feature Workflow

`fuggers-py` uses one explicit entrypoint for spec-first feature work:

```text
$add-feature <feature request>
```

That trigger must use the repo skill:

- `.agents/skills/add-feature/SKILL.md`

## Required files

For feature slug `<feature-slug>`:

- `.tmp/add-feature/specs/<feature-slug>.json`

## Temporary workflow files

The validator keeps the active workflow spec and review files in temporary
paths and removes them when the workflow is marked passed or cleared:

- `.tmp/add-feature/specs/<feature-slug>.json`

- `.tmp/add-feature/reviews/<feature-slug>.fi_api_reviewer.md`
- `.tmp/add-feature/reviews/<feature-slug>.fi_finance_reviewer.md`
- `.tmp/add-feature/reviews/<feature-slug>.fi_diff_reviewer.md`

## Required pytest markers

Every feature-owned test needs both markers:

```python
import pytest

@pytest.mark.feature_slug("<feature-slug>")
@pytest.mark.feature_category("<category>")
def test_example() -> None:
    ...
```

## Category map

- `unit` -> `tests/unit/`
- `validation` -> `tests/integration/validation/`
- `properties` -> `tests/integration/properties/`
- `workflow` -> `tests/integration/workflows/`
- `api_contract` -> `tests/contracts/api/`
- `architecture_contract` -> `tests/contracts/architecture/`
- `docs_smoke` -> `tests/contracts/docs/`
- `examples_smoke` -> `tests/integration/examples/`

For fixed-income features, the default minimum categories are:

- `unit`
- `validation`
- `properties`

Additional categories become required when the feature shape demands them:

- `api_contract` for public API additions or public API changes
- `workflow` for `calc/` or `portfolio/` workflow changes
- `docs_smoke` for docs or `README.md` changes
- `examples_smoke` for example changes

## Commands

Start:

```bash
python tools/validate_add_feature.py init --slug <feature-slug>
```

Finish:

```bash
python tools/validate_add_feature.py validate --mark-passed
```

Checkpoint during work:

```bash
python tools/validate_add_feature.py validate
```

Run the full repo-wide gate without closing the workflow:

```bash
python tools/validate_add_feature.py validate --full
```

Inspect current state:

```bash
python tools/validate_add_feature.py status
```

Clear a stale workflow:

```bash
python tools/validate_add_feature.py clear --slug <feature-slug>
```

The Stop hook uses `.tmp/add-feature/.state.json` and blocks completion until the workflow is marked passed.
`validate --mark-passed` and `clear` remove the temporary spec, review files, and workflow state.
Plain `validate` is the fast checkpoint path.
`validate --full` and `validate --mark-passed` run the heavyweight repo-wide checks.
