# Changelog

All notable changes to this project are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

Development toward 1.0.0. No release yet; the version in `pyproject.toml` is
`1.0.0.dev0`.

### Added - testing
- Test suite (`tests/`), written with **pytest + pytest-django**: 40 tests,
  runnable on SQLite, PostgreSQL and MySQL via `DB_BACKEND`, and in parallel
  via `pytest -n auto` (pytest-xdist). The repository previously shipped an
  empty test file.
- `tox.ini` with a Django 3.2 -> 6.1 matrix, plus a `djmain` environment that
  tracks Django's unreleased main branch with `ignore_outcome = true`.
  `pytest-django` is pinned per Django factor because no single release spans
  3.2 to 6.1.
- Deprecation warnings are errors, via both `PYTHONWARNINGS` (which covers
  collection-time imports) and pytest's `filterwarnings`. This is the control
  that would have caught the `providing_args` removal in Django 3.0, two years
  before Django 4.0 broke the package.

### Added - packaging
- `pyproject.toml` (PEP 621), replacing `setup.py`. Declares a `Django>=5.2`
  floor with no upper cap, and advertises supported versions through
  `Framework :: Django ::` classifiers proven by the tox matrix.
- Publishing moved to **uv** (`uv build` / `uv publish`); `twine` is no longer
  used. See `RELEASING.md`. Note that uv does not read `~/.pypirc`.
- `.github/workflows/release.yml` publishes on a tag push using **Trusted
  Publishing (OIDC)**, so no PyPI token exists in the repo, in secrets, or on
  any developer machine.
- Regenerated `uv.lock`, whose `requires-python` had drifted to `>=3.11`.

### Added - lint and formatting
- Ruff at maximum strictness: `select = ["ALL"]`, with every exemption
  individually justified in `pyproject.toml`. The package source and the test
  suite are both fully compliant, and `ruff format` is applied repo-wide.
- `.pre-commit-config.yaml` running ruff (check + format), file-hygiene hooks,
  gitleaks and zizmor. CI runs the identical hook set, so lint has one source
  of truth rather than two.

### Added - security scanning
`.github/workflows/security.yml`, on every push, pull request, and daily.
All six jobs run in parallel:

| Job | Covers |
| --- | --- |
| `codeql` | SAST over our own code (`security-extended`) |
| `dependencies` | `pip-audit` against the PyPI Advisory Database |
| `osv` | OSV-Scanner, a second vulnerability database |
| `workflows` | `zizmor` - GitHub Actions supply-chain auditing |
| `secrets` | `gitleaks` over full git history |
| `scorecard` | OpenSSF Scorecard supply-chain posture |

Bandit-class SAST is additionally covered inline by ruff's `S` ruleset, which
`select = ["ALL"]` enables.

Workflow hardening applied after an initial zizmor audit reported 32 findings
(12 high): every action is pinned to a commit SHA rather than a mutable tag,
every workflow and job declares least-privilege `permissions`, checkouts use
`persist-credentials: false`, and the release build runs without a cache to
close a cache-poisoning path into a published artifact. Zizmor now reports no
findings. Dependabot keeps the SHA pins current, with a 7-day cooldown so a
freshly published version is not adopted immediately.

### Known bugs, reproduced by the test suite
Eleven tests are strict xfails (`pytest.mark.xfail(strict=True)`), so CI is
green today but any fix becomes an *unexpected pass* and fails the build,
forcing the marker to be removed:

1. `Signal(providing_args=...)` - unimportable on Django >= 4.0.
2. Generators passed to `bulk_create()`/`bulk_update()` are consumed while
   building the signal payload, so the operation is a silent no-op.
3. `bulk_create()` re-declares Django 4.0's signature, so Django 4.1's
   `update_conflicts`/`update_fields`/`unique_fields` raise `TypeError`. This
   also makes `abulk_create()` unusable.
4. `update(<fk>_id=...)` raises `KeyError` - FK attnames are not field names.
5. `ValidationError(detail=..., code=...)` is DRF's signature, not Django's, so
   every error path raises `TypeError` instead.
6. A bare `F()` is not an `Expression`, so it slips past the guard and crashes.
7. `bulk_update()` issues one `SELECT` per object (26 queries for 25 objects).
8. That per-object lookup uses the default manager and ignores `self.db`, so a
   filtered manager raises `DoesNotExist` and multi-db reads the wrong database.
9. `update()` calls `.exists()` and then materialises the entire queryset.

The lint pass added annotations and docstrings throughout the package source
but deliberately changed no behaviour: every bug above is preserved, documented
inline with a `KNOWN BUG #n` note, and the full matrix produces byte-identical
results before and after.

### Notes
- `main.py` is PyCharm scaffolding, excluded from lint and packaging. It can be
  deleted.
- `django_bulk_signals/__init__.py` now uses explicit imports and `__all__`
  instead of `import *`. The documented API is unchanged; incidental
  re-exports (`django_bulk_signals.models`, `.ValidationError`) are gone.

## [0.1.1] - 2026-09-10

Metadata-only release. **No code changes** — the package behaves exactly as
0.1.0 on Django 3.x.

### Fixed
- Capped the Django requirement at `Django>=3.2,<4.0`. Django 4.0 removed the
  `providing_args` argument to `django.dispatch.Signal`, which this package
  passes at import time, so 0.1.0 raises
  `TypeError: Signal.__init__() got an unexpected keyword argument 'providing_args'`
  on every Django from 4.0 onward. 0.1.0 declared `Django>=3.2` with no upper
  bound and could therefore be installed into projects it cannot run on.
- Corrected the install command in the README. It previously read
  `pip install django-bulk-signals`, which is an unrelated project by a
  different author. The correct name is `django-advanced-bulk-signals`.
- `setup.py` no longer leaks an open file handle when reading `README.md`, and
  resolves it relative to the file rather than the current directory.
- `find_packages()` is now scoped to `django_bulk_signals*`.

### Added
- `MANIFEST.in`, so the source distribution includes `README.md`, `LICENSE`
  and this changelog. 0.1.0 shipped a wheel only.
- Accurate `Framework :: Django :: 3.2` and Python version classifiers.

### Known issues
This release still contains the behavioural bugs found in the 2026-09-10 audit
(silent no-op on generator input, `KeyError` on `update(<fk>_id=...)`, N+1
queries in `bulk_update()`, full queryset materialisation in `update()`, and
others). They are reproduced by the test suite added in the next release and
will be fixed in 1.0.0, which will also lift the Django cap.

## [0.1.0] - 2025-05-08

Initial release, extracted from an internal project. Targets Django 3.2.
