# 🛠️ Development setup

Afanes runs from a source checkout. Hatch is the only supported developer interface: it creates the
environment, runs the application, and exposes the checks.

:::{admonition} tl;dr
:class: note

Run `hatch env create`, then `hatch run afanes`. Use `hatch check` for lint, format, and types, and
`hatch test --cover` for the test suite.
:::

## 🧰 Prerequisites

- Python 3.13 or newer.
- [Hatch](https://hatch.pypa.io/) for every developer command.
- The Flutter SDK and native build tools only when you build a packaged desktop artifact.

Do not create or edit `.venv/` by hand, and do not use `uv`, `pip`, `poetry`, or `conda` as the
developer interface. `hatch env create` owns the environment.

## 🚀 Run the application

```console
hatch env create
hatch run afanes
hatch run afanes --web
```

The first command creates the development environment. `hatch run afanes` opens the desktop window;
`hatch run afanes --web` serves the loopback browser presentation. `hatch run python -m afanes` is the
module form of the same launch.

## ✅ Checks

```console
hatch check
hatch check --fix
hatch test --cover
hatch test --all
```

- `hatch check` runs Ruff lint, Ruff format verification, and Pyrefly strict type checking.
- `hatch check --fix` applies lint and format fixes; type errors still need manual changes.
- `hatch test --cover` runs the suite with the coverage floor.
- `hatch test --all` runs the supported interpreters and the oldest dependency floor.

Run the narrowest relevant test while iterating:

```console
hatch test tests/core/vault/test_service.py::TestVaultOpen::test_opens_an_existing_directory
hatch test -k "frontmatter and not slow"
```

Use `hatch run pytest ...` only for focused diagnosis.

## 📦 Dependencies

Runtime dependencies use compatible ranges in `pyproject.toml`, with the lower bound tested by the
floor matrix. There is no lock or constraints file. Documentation tools live in the `docs` dependency
group and are installed only by the `docs` Hatch environment.

A new dependency needs an approved OpenSpec change covering the need, alternatives, license, offline
behavior, and cross-platform impact. Never add cloud, telemetry, or auto-update packages.

## 🧭 See also

- [Architecture](architecture.md)
- [Testing](testing.md)
- [Documentation guide](documentation.md)
- [AGENTS.md](https://github.com/knkillname/afanes/blob/main/AGENTS.md) for the full operating rules
