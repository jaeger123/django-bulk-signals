# Releasing

## Before anything

```bash
uvx pre-commit install      # once, per clone
uvx pre-commit run --all-files
tox                         # the full Django 3.2 -> 6.1 matrix
```

Publishing uses [`uv`](https://docs.astral.sh/uv/). There is no `setup.py`, no
`python -m build`, and no `twine`.

## One gotcha first

**`uv` does not read `~/.pypirc`.** If you have credentials there from a
previous `twine` setup, `uv publish` will ignore them and fail with:

```
Note: Neither credentials nor keyring are configured, and there was an error
fetching the trusted publishing token.
error: Trusted publishing failed
```

That is an authentication problem, not a packaging one. uv takes credentials
from `UV_PUBLISH_TOKEN` / `--token`, from keyring, or from Trusted Publishing
(OIDC) in CI.

## Preferred: release from CI

Publishing runs on a tag push via `.github/workflows/release.yml` using
**Trusted Publishing**, so no API token exists anywhere - not in the repo, not
in secrets, not on your laptop.

One-time setup on PyPI, under
*Manage project -> Publishing -> Add a new publisher*:

| Field | Value |
| --- | --- |
| Owner / repository | your GitHub org / repo |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

Then, to release:

```bash
# 1. bump the version
uv version 1.0.0                  # writes pyproject.toml

# 2. update CHANGELOG.md, commit
git commit -am "Release 1.0.0"

# 3. tag and push - this triggers the release workflow
git tag v1.0.0
git push origin main --tags
```

The workflow builds, checks that the tag matches `uv version --short`, smoke
-imports the built wheel, then publishes. Adding a required reviewer to the
`pypi` GitHub environment turns the publish step into a manual approval gate.

## Releasing from your machine

```bash
# build sdist + wheel into dist/
uv build --clear

# always rehearse first - validates the files against the real endpoint
uv publish --dry-run

# TestPyPI (the index is preconfigured in pyproject.toml)
uv publish --index testpypi

# PyPI
uv publish
```

Provide the token in whichever way you prefer:

```bash
export UV_PUBLISH_TOKEN='pypi-...'        # then just `uv publish`
uv publish --token 'pypi-...'
uv publish --keyring-provider subprocess -u __token__
```

If your token is already in `~/.pypirc`, this bridges it across for one command
without copying it anywhere:

```bash
UV_PUBLISH_TOKEN=$(python3 -c "import configparser,os;c=configparser.ConfigParser();c.read(os.path.expanduser('~/.pypirc'));print(c['pypi']['password'])") uv publish
```

## Useful flags

| Flag | Why |
| --- | --- |
| `--dry-run` | Validate without uploading. Always do this first. |
| `--check-url https://pypi.org/simple/django-advanced-bulk-signals/` | Skip files already uploaded, so a partially-failed release can be retried safely. |
| `--index testpypi` | Publish to TestPyPI (configured in `pyproject.toml`). |
| `--trusted-publishing always` | Fail loudly in CI rather than silently falling back to a token. |

`uv publish` uploads [PEP 740 attestations](https://peps.python.org/pep-0740/)
automatically when publishing via Trusted Publishing; `--no-attestations`
disables that.

## Verifying a release

```bash
uv run --isolated --no-project --with django-advanced-bulk-signals \
  python -c "import django_bulk_signals; print('ok')"
```

## Note on 0.1.1

The 0.1.1 artifacts in `dist/` were built with `setup.py` before the migration
to `pyproject.toml`, and were verified by hand (`twine check`, plus install
tests confirming the `Django<4.0` cap makes a Django 6.1 install unsatisfiable).
They can be published as-is with `uv publish`, which only uploads files and
does not care what built them. Everything from 1.0.0 onward goes through
`uv build`.
