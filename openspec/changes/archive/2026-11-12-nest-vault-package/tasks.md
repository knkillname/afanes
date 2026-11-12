# Tasks

## 1. Move the modules

- [x] 1.1 Create `src/afanes/core/vault/` and move the six modules to `service.py`, `snapshot.py`, `naming.py`, `pages.py`, `steps.py`, and `processing.py`; add a docstring-only `__init__.py`; verify no `core/vault_*.py` file remains.
- [x] 1.2 Create `tests/core/vault/` and move the six mirror test modules to `test_service.py`, `test_snapshot.py`, `test_naming.py`, `test_pages.py`, `test_steps.py`, and `test_processing.py`; add `tests/core/vault/__init__.py`; verify assertions are unchanged.

## 2. Rewrite the imports

- [x] 2.1 Rewrite `src/` imports from `afanes.core.vault_*` to `afanes.core.vault.*` and from `afanes.core.vault.Vault` to `afanes.core.vault.service.Vault`; verify `hatch check types` passes.
- [x] 2.2 Rewrite `tests/` and `scripts/` imports the same way; verify no file still references a flat `vault_*` module.
- [x] 2.3 Update docstring cross-references and error copy that name `core/vault.py` or `core/vault_*.py`.

## 3. Update the gate and the docs

- [x] 3.1 Repoint `test_vault_does_not_import_its_sibling_services` at `core/vault/service.py` and the `afanes.core.vault.*` sibling names; verify the gate passes and fails when a sibling import is introduced.
- [x] 3.2 Update the `AGENTS.md` test-path example and any flat-module wording; verify section citations still resolve.
- [x] 3.3 Update the `CHANGELOG.md` Unreleased migration entries to the package paths and name this change.

## 4. Integration checks

- [x] 4.1 Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, `openspec doctor`, and the compliance greps; verify all pass.
