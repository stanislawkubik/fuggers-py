# Releasing

`fuggers-py` uses `setuptools_scm`, so supported release builds must be run from a normal git checkout (or tag checkout) with `.git` metadata present.

Do not cut release artifacts from an exported/copied source tree that no longer has SCM metadata attached. In that case `setuptools_scm` falls back to the configured development version, which is fine for scratch snapshots but not a publishing path.

The package is already configured for PyPI publishing through GitHub Actions on version tags. This file exists to document the parts of the release path that are easy to forget but are not obvious from `pyproject.toml` or `.github/workflows/release.yml`.

## Local validation from a normal checkout

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev,engine,examples]"
pytest -q
pytest -q tests/integration/validation tests/integration/properties/test_property_invariants.py tests/integration/examples/test_examples_smoke.py
ruff check src/fuggers_py tools/source_coverage.py tests/contracts/api/test_optional_dependencies.py typecheck tools/run_release_ruff.py tools/packaging
python tools/run_release_ruff.py
mypy
python tools/source_coverage.py --pytest-args -q
PYTHONPATH=src pytest -q tests/integration/examples/test_examples_smoke.py
python -m build
python -m pip wheel . --no-deps -w /tmp/fuggers-pip-wheel-check
python -m twine check dist/*
python -m venv /tmp/fuggers-release-artifact-venv
/tmp/fuggers-release-artifact-venv/bin/pip install --upgrade pip
/tmp/fuggers-release-artifact-venv/bin/pip install dist/fuggers_py-*.whl
/tmp/fuggers-release-artifact-venv/bin/python -c "import fuggers_py; print(fuggers_py.__version__)"
```

Both `python -m build` and `python -m pip wheel . --no-deps -w <dir>` are supported from a normal git checkout and must produce the same version metadata. Treat any mismatch between editable install, built wheel, built sdist, pip-wheel output, and installed metadata as a release blocker.

For a stable release tag such as `v0.2.0`, the resolved version must be exactly `0.2.0`:

- no `.dev*`
- no `+local` suffix
- no `a`, `b`, or `rc` pre-release segment

## Automated publish path

Pushing a tag matching `v*` triggers `.github/workflows/release.yml`.

The workflow:

- builds wheel and sdist
- verifies exact tagged version provenance
- smoke-tests installed wheel and sdist paths
- publishes the built distributions to PyPI through Trusted Publishing

## Cutting a release

1. Ensure `main` is clean, ready, and CI is green.
2. Update `CHANGELOG.md` as needed.
3. Optionally validate the exact stable tag locally before pushing:

```bash
git tag v0.2.0
EXPECTED_RELEASE_VERSION=0.2.0 pytest -q tests/contracts/packaging/test_packaging_version_consistency.py
git tag -d v0.2.0
```

4. Push the release tag:

```bash
git tag v0.2.0
git push origin main
git push origin v0.2.0
```

`setuptools_scm` maps the Git tag `v0.2.0` to the package version `0.2.0`.

No packaging-file edits should be required for a normal release.
