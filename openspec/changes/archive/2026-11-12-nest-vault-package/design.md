# Design

## Context

See `proposal.md` - Why. `split-vault-service` produced six flat modules whose
sizes are:

| Module | Lines | Main symbol |
| --- | --- | --- |
| `core/vault.py` | 695 | `Vault`, `VaultCreation` |
| `core/vault_snapshot.py` | 815 | snapshot and path value types |
| `core/vault_naming.py` | 877 | `VaultNaming` |
| `core/vault_processing.py` | 449 | `VaultProcessing` |
| `core/vault_pages.py` | 349 | `VaultPages` |
| `core/vault_steps.py` | 275 | `VaultSteps` |

Every module is already below the 900-line ceiling, so this change is purely
about where they live and what they are called.

## Goals / Non-Goals

**Goals:**

- Present the vault services as one package.
- Keep the import graph acyclic and the `core` layering unchanged.
- Keep every class and function name unchanged.
- Keep the package front door thin.

**Non-Goals:**

- Merging or renaming classes.
- Changing any method signature, behavior, exception, or file format.
- Re-exporting `Vault` or the services from `vault/__init__.py`.
- Adding a compatibility shim for the old flat modules.

## Decisions

### D1. Package layout

```
core/vault/
  __init__.py     module docstring only
  service.py      Vault, VaultCreation
  snapshot.py     snapshot, note, failure, path, ordering, page result types
  naming.py       VaultNaming and the preview/report types
  pages.py        VaultPages
  steps.py        VaultSteps
  processing.py   VaultProcessing
```

`service.py` is chosen over `vault.py` inside the package to avoid
`afanes.core.vault.vault`; it also matches the service-object vocabulary in
`AGENTS.md` 4.2. The class keeps the public name `Vault`.

### D2. Thin `__init__.py`, no re-exports

`AGENTS.md` 3.2 asks for a thin package init and prohibits re-exporting
implementation symbols. `vault/__init__.py` therefore contains only a module
docstring. Callers import the class from its defining module:

```python
from afanes.core.vault.service import Vault, VaultCreation
```

Class imports are allowed by the import rules; module imports remain the rule
for functions and constants (`import afanes.core.vault.naming`).

### D3. No compatibility shim

A `core/vault.py` module cannot coexist cleanly with a `core/vault/` package:
Python would resolve one and make the other unreachable. Every call site moves
in this change. The repository is pre-1.0 and the module paths are internal, so
no deprecation window is needed; `CHANGELOG.md` records the new paths.

### D4. Gate follows the package

`test_vault_does_not_import_its_sibling_services` reads
`core/vault/service.py` and checks `afanes.core.vault.{naming,pages,steps,
processing}`. The existing 900-line and 20-method budgets already walk
`core/` recursively, so they cover the package without a new rule.

### D5. Mirror the tests

`AGENTS.md` 4.7 asks tests to mirror `src/`. The six test modules move to
`tests/core/vault/test_{service,snapshot,naming,pages,steps,processing}.py`
with assertions unchanged. `tests/core/vault/__init__.py` mirrors
`src/afanes/core/vault/__init__.py`.

## Risks / Trade-offs

- [A mechanical import rename touches many files] -> Use one deterministic
  rewrite and let `hatch check` plus the import-cycle gate catch misses.
- [Tests move and coverage paths change] -> No assertion changes; run
  `hatch test --cover` after the move.
- [A caller keeps importing `afanes.core.vault.Vault`] -> The import fails
  loudly with `ImportError`; the type checker also reports it, so no silent
  fallback exists.
- [Someone adds a new flat `vault_*` module later] -> The package now makes the
  intended home obvious; the architecture gate still caps module size and
  sibling imports.

## Migration Plan

1. Create `src/afanes/core/vault/` and `tests/core/vault/`; move the six source
   modules and six test modules; add both `__init__.py` files.
2. Rewrite imports in `src/`, `tests/`, and `scripts/`.
3. Repoint the architecture gate and update `AGENTS.md` and `CHANGELOG.md`.
4. Run `hatch check`, `hatch test --cover`, `openspec validate --all
   --strict`, `openspec doctor`, and the compliance greps.

## Open Questions

None. The package name, the `service.py` filename, the thin init, and the test
mirror are confirmed.
