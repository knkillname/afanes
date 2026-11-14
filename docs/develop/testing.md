# 🧪 Testing

The test suite is part of the developer interface: `hatch test` owns the environment, and the tests are
the executable record of the behavior in `openspec/specs/`.

:::{admonition} tl;dr
:class: note

Run `hatch test --cover` before reporting a change ready. Put tests under a path that mirrors `src/`,
use local fixtures and `tmp_path`, and never touch the real vault or the network.
:::

## ▶️ Commands

```console
hatch test --cover
hatch test tests/core/vault/test_service.py::TestVaultOpen::test_opens_an_existing_directory
hatch test -k "frontmatter and not slow"
hatch test --all
```

`--cover` enforces the coverage floor. `--all` runs the supported interpreters and the oldest
dependency floor. Use `hatch run pytest ...` only when you need focused diagnosis outside the standard
matrix.

## 🧱 Layout and conventions

Tests mirror `src/` under `tests/`: `tests/core/vault/test_service.py` mirrors
`src/afanes/core/vault/service.py`. Fixtures are local or autouse; the shared `tests/conftest.py`
only compiles the generated gettext catalogs before the suite runs.

- Use `Test<Behavior>` classes and names that describe behavior.
- One behavior per test; arrange, act, assert.
- Use `tmp_path` and fixture-created vaults. Never touch the real vault, the home directory, or the
  network.
- Reset the UI singleton in UI tests: `afanes.ui.state.app_state.reset()`.
- Use Hypothesis for parser round-trips, reference extraction, name normalization, filename
  sanitization, path containment, and frontmatter types. Add a deterministic regression test for every
  minimized failure.
- Do not import, call, monkeypatch, or test leading-underscore members. Promote the behavior if it needs
  coverage.

`pytest-randomly` is active, so tests must not depend on order or shared mutable state. `--strict-markers`
is on and no custom markers are registered; register any marker in `pyproject.toml`.

## 📊 Coverage

The coverage minimum is 85% (`fail_under`). Parser, link, and vault modules should stay at 90% or
higher. A bug fix needs a regression test; new behavior needs a test that would fail without it.

## 🧭 See also

- [Development setup](setup.md)
- [Architecture](architecture.md)
- [Documentation guide](documentation.md)
