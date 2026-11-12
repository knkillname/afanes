# Tasks

## 1. Extract the snapshot types

- [x] 1.1 Move `VaultNote`, `VaultFailure`, `VaultSnapshot`, `LinkTarget`, `LinkOutcome`, `ReferenceSite`, `NoteOrder`, `InboxOrder`, `VaultPath`, `NotePath`, `PageFile`, `ParsedPage`, and `UnparsedPage` into `core/vault_snapshot.py`; verify `hatch test tests/core/test_vault.py` and the import-cycle gate pass.
- [x] 1.2 Update the imports in `core/`, `ui/`, `cli/`, and `tests/` to the new module; verify `hatch check types` passes with no unused-import findings.
- [x] 1.3 Move the snapshot tests into `tests/core/test_vault_snapshot.py`; verify the assertions are unchanged and `hatch test tests/core/` passes.

## 2. Extract the write services

- [x] 2.1 Extract `VaultNaming` into `core/vault_naming.py` with rename, category move, reference repair, trash, and the preview/report types; verify the naming and trash tests pass.
- [x] 2.2 Extract `VaultProcessing` into `core/vault_processing.py` with the processing and append-step plans and their apply path; verify the processing and integration tests pass.
- [x] 2.3 Extract `VaultPages` into `core/vault_pages.py` with capture, create, write, recreate, and label changes; verify the page and capture tests pass.
- [x] 2.4 Extract `VaultSteps` into `core/vault_steps.py` with tick, untick, plan, append, and owner changes; verify the step tests pass.
- [x] 2.5 Remove the extracted methods and their private helpers from `Vault`; verify an AST count shows `Vault` at or under the public-method budget and no duplicate method remains.

## 3. Enforce and document the boundary

- [x] 3.1 Add the three gate rules from design D5 (20 public methods per class, 900 lines per module, and no sibling imports from `core/vault.py`) to `tests/core/test_architecture.py`; verify the gate passes and fails when a temporary violation is introduced.
- [x] 3.2 Reorganize `tests/core/` so each new module has a mirror test file; verify `hatch test --cover` stays at or above 85 percent and the parser, link, and vault modules stay at or above 90 percent.
- [x] 3.3 Add the `Unreleased` changelog entry listing every moved public method with its new owner and call form; verify each entry names a replacement.

## 4. Integration checks

- [x] 4.1 Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, `openspec doctor`, and the 6.6 compliance check; verify all pass.
