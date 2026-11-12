# Proposal

## Why

`split-vault-service` left six sibling modules directly under `core/`:
`vault.py`, `vault_snapshot.py`, `vault_pages.py`, `vault_steps.py`,
`vault_processing.py`, and `vault_naming.py`. The `vault_` prefix is a naming
smell: the underscore form exists only because a module cannot share a name with
a package. The split also makes one feature look like six unrelated `core/`
modules, and it clutters the `core/` listing for every reader.

A `core/vault/` package shows that these modules are one feature, keeps the
service names short (`naming.py`, `pages.py`, ...), and stops new `vault_*`
siblings from being added flat beside unrelated core modules.

## What Changes

- Move the six modules into `src/afanes/core/vault/`:
  - `vault.py` -> `vault/service.py` (`Vault`, `VaultCreation`)
  - `vault_snapshot.py` -> `vault/snapshot.py`
  - `vault_naming.py` -> `vault/naming.py`
  - `vault_pages.py` -> `vault/pages.py`
  - `vault_steps.py` -> `vault/steps.py`
  - `vault_processing.py` -> `vault/processing.py`
- Add a thin `vault/__init__.py` with only a module docstring; do not re-export
  `Vault` or any service.
- Update every import in `src/`, `tests/`, and `scripts/` to the package paths.
- Repoint the architecture gate's sibling-import rule and the `Vault` path.
- Mirror the tests under `tests/core/vault/`.
- Update the `AGENTS.md` example path and the `CHANGELOG.md` migration entry.

## Capabilities

None. This is a pure layout refactor; no behavior, file format, exception,
UI copy, or CLI flag changes. `skip_specs: true` is declared in
`.openspec.yaml`.

### New Capabilities

- None.

### Modified Capabilities

- None.

## Impact

- `src/afanes/core/vault/` becomes a package; `core/vault.py` and the five
  `core/vault_*.py` modules disappear.
- Importers change from `afanes.core.vault_naming` to
  `afanes.core.vault.naming`, and from `afanes.core.vault` to
  `afanes.core.vault.service` for the `Vault` class.
- `tests/core/test_vault.py` and the five sibling test files move to
  `tests/core/vault/`.
- `tests/core/test_architecture.py`, `AGENTS.md`, and `CHANGELOG.md` follow.
- No vault file, frontmatter key, dependency, or runtime behavior changes.

## Open Questions

None. The maintainer confirmed a `core/vault/` package with `service.py` for the
shared `Vault` service and short sibling module names.
