# Contributing

Thanks for taking the time to contribute to `fuggers-py`.

This is a fixed-income research and production library. Contributions are welcome, but please keep changes focused, readable, and well-tested.

The project is still pre-`1.0`. Public APIs are already broad, but they are not
fully frozen yet. When a change affects user-facing names, structure, or
behavior, please also update [docs/STATUS.md](docs/STATUS.md) if the maturity
or readiness story changed.

## Before you start

If you found a bug, have a feature idea, or want to change part of the API, please open an issue first.

For very small fixes, you can open a pull request directly.

If the change is larger, touches public APIs, or changes library conventions, it is better to discuss it in an issue before spending time on implementation.

## Development setup

Install the project in editable mode with the development tools:

```bash
python -m pip install -e ".[dev,engine,examples]"
```

## Making changes

Please keep changes small and easy to review.

When you change code:

- add or update tests in `tests/`
- update notebooks in `examples/` when the changed module should be demonstrated there
- update docs in `docs/` if behavior, APIs, or conventions changed
- review `README.md` and update it if it is no longer accurate

Library code lives under `src/`.

The test tree is split into:

- `tests/unit/` for package-level unit coverage
- `tests/integration/` for workflows, examples, validation, and property checks
- `tests/contracts/` for API, docs, packaging, and tooling contracts
- `tests/fixtures/` for shared data and golden fixtures

## Checks to run

At a minimum, please run:

```bash
pytest -q
```

If your change affects packaging, typing, examples, or release-related behavior, please also run the relevant extra checks from the repo before opening the pull request.

## Pull requests

Please open pull requests against `main`.

A good pull request should:

- explain what changed
- explain why it changed
- mention any user-visible API or behavior changes
- point to the related issue if there is one

If a pull request is still exploratory or not ready for review, say that clearly in the description.

## Style

Prefer simple code over clever code.

Please avoid adding unnecessary abstraction, fallback logic, or defensive machinery unless it is clearly needed. This library is used for research as well as production work, so clarity matters.

## Questions

If anything is unclear, open an issue and ask.
