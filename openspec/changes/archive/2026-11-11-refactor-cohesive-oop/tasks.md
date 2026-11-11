# Tasks

## 1. Directive and shared atomic writer

- [x] 1.1 Add `src/afanes/core/atomic.py` with `write_text_atomic` moved unchanged from `core/vault.py`; update `core/vault.py` and `core/settings.py` to call it; move the atomic-writer tests to `tests/core/test_atomic.py`; verify `hatch test tests/core/test_atomic.py tests/core/test_vault.py tests/core/test_settings.py` passes.
- [x] 1.2 Add a `#### Object boundaries` subsection under `AGENTS.md` section 4.3 with the value-object, service-object, pure-function, and controller/view roles, the review rules, and the checklist; update the "Cohesive objects over function bags" bullet to reference it and include `Settings` and `Vault` as examples; verify the vocabulary compliance check in `AGENTS.md` section 6.6 exits clean.
- [x] 1.3 Update `AGENTS.md` section 3.1 to list `core/atomic.py` and section 4.9 to name it as the shared atomic primitive called by `core/vault.py` and `core/settings.py`; verify the documented layout and file-I/O policy match the code.
- [x] 1.4 Add an architecture test that `core/atomic.py` imports only the standard library and `afanes.core.errors`; verify `hatch test tests/core/test_architecture.py` passes.

## 2. Settings value object and store

- [x] 2.1 Add `Settings.from_payload` and `Settings.to_payload`; move the validation out of `_settings_from_payload` and delete that function; add direct tests for valid, malformed, unsupported-version, non-object, missing-vault, and relative-vault payloads; verify `hatch test tests/core/test_settings.py` passes.
- [x] 2.2 Add `SettingsStore(path)` with `default()`, `load()`, and `save()`; remove `load_settings` and `save_settings`; migrate `tests/core/test_settings.py` to the store and patch `afanes.core.atomic.write_text_atomic` for write failures; verify `hatch test tests/core/test_settings.py` passes.
- [x] 2.3 Update `AppState.start` and `choose_vault` to use `SettingsStore.default()`; update the save-failure test to patch `SettingsStore.save`; verify `hatch test tests/ui/test_state.py` passes.
- [x] 2.4 Update `tests/ui/test_app.py` settings seeding to use `SettingsStore(settings).save(Settings(vault=vault))`; verify `hatch test tests/ui/test_app.py tests/ui/test_inbox_view.py` passes.
- [x] 2.5 Add an architecture test that `core/settings.py` does not import `core/vault.py`; verify `hatch test tests/core/test_architecture.py` passes.

## 3. Vault service and snapshot query

- [x] 3.1 Add `Vault(root)` with a resolved, validated root and a `contained(candidate)` method; add tests for resolving a directory, rejecting a file or missing directory, relative/absolute containment, traversal, and escaping symlinks; verify `hatch test tests/core/test_vault.py` passes for the new tests while the old free functions still exist.
- [x] 3.2 Add `Vault.scan()` and `Vault.read_body()`, and move `inbox_notes` onto `VaultSnapshot`; migrate the scan, inbox, and preview call sites and tests; remove `resolve_vault_root`, `contained_path`, `scan_vault`, and `inbox_notes`; verify `hatch test tests/core/test_vault.py tests/core/test_integration.py tests/ui/test_state.py` passes.
- [x] 3.3 Add `Vault.create()` and `Vault.capture()`; migrate the creation and capture tests and `AppState.capture`; remove `create_note` and `capture_note`; verify `hatch test tests/core/test_vault.py tests/core/test_integration.py tests/ui/test_state.py` passes.
- [x] 3.4 Add `Vault.move()`, `Vault.plan_rename()`, and `Vault.apply_rename()`; migrate the move and rename tests; remove `move_note`, `plan_rename`, and `apply_rename`; verify `hatch test tests/core/test_vault.py tests/core/test_integration.py` passes.
- [x] 3.5 Add `Vault.plan_deletion()` and `Vault.delete()`; migrate the deletion tests; remove `plan_deletion` and `delete_note`; verify `hatch test tests/core/test_vault.py` passes.
- [x] 3.6 Refactor `AppState` to store `Vault | None`, expose a read-only `vault_root` property, use `Vault` methods in `start`, `choose_vault`, `refresh`, `capture`, and `select_note`, and replace the module-level `_open_vault` and `_read_body` helpers; verify `hatch test tests/ui/test_state.py tests/ui/test_app.py tests/ui/test_inbox_view.py` passes.
- [x] 3.7 Migrate any remaining UI test seeding from `afanes.core.vault` free functions to `Vault`; verify `hatch test tests/ui/` passes.

## 4. Reference reader

- [x] 4.1 Add `ReferenceReader` with one `MarkdownIt("commonmark")` parser and an `extract` method; move the extraction tests to the reader, remove `extract_references`, and add a test that one reader extracts from two documents and still ignores code, comments, and images; verify `hatch test tests/core/test_links.py` passes.
- [x] 4.2 Update `Vault.scan` and its note reader to share one `ReferenceReader` per scan, and update `_rewrite_note` and `_verify_rewrite` to use the reader; verify `hatch test tests/core/test_links.py tests/core/test_vault.py` passes.
- [x] 4.3 Confirm `NameCatalog`, `parse_reference`, `classify_destination`, `reference_key`, `rewrite_body_references`, and the Markdown span helpers remain public/module-level stateless functions; verify the links tests and the architecture import graph still pass.

## 5. Integration and quality gates

- [x] 5.1 Run `git grep` for every removed public symbol in `src/` and `tests/` and verify no call sites remain; update the migration map in `design.md` if any name changed during implementation.
- [x] 5.2 Run `hatch check`; verify it passes with zero type errors.
- [x] 5.3 Run `hatch test --cover`; verify all tests pass and overall coverage remains at least 85%.
- [x] 5.4 Run `openspec validate --all --strict` and `openspec doctor`; verify both pass.
- [x] 5.5 Run the vocabulary compliance check from `AGENTS.md` section 6.6, using `git grep` with the same patterns if `rg` is unavailable; verify it exits clean.
- [x] 5.6 Review the diff for behavior parity: settings JSON, vault format, error text, ordering, atomicity, confirmation gates, and platform paths unchanged; verify no new network clients, dependencies, or telemetry and record the review in the change.

## Workflow follow-up

- Review the completed change with the maintainer.
- Archive with `/opsx-archive refactor-cohesive-oop` after approval.
- At archive, classify the public API removal as a breaking change per `AGENTS.md` section 5.8, update `CHANGELOG.md`, and review `README.md` (record `README: no change required` if the source-run and vault documentation remains accurate).
- Run the post-archive release workflow and quality gates.
