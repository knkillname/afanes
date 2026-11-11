# Tasks

## 1. Domain model and parsing

- [x] 1.1 Update `src/afanes/models/note.py` to remove `NoteType.PERSON`, add `ReferenceCategory` with `PERSON`, and add `Status` with `active`, `waiting`, `done`, `cancelled`, `archived`, and `later`; update `tests/models/test_note.py` for members and string values; verify `hatch test tests/models/test_note.py` passes.
- [x] 1.2 Extend `NoteDocument` in `src/afanes/core/frontmatter.py` with `category` and `status`; validate category only on references, known lowercase values, and the per-type status matrix; preserve unknown keys; add tests in `tests/core/test_frontmatter.py`; verify `hatch test tests/core/test_frontmatter.py` passes.
- [x] 1.3 Update scheme mapping and `NameCatalog` in `src/afanes/core/links.py` to accept type plus optional category, map `person` to reference notes with `category: person`, and keep one note in one scheme; add and update tests in `tests/core/test_links.py`; verify the file passes.
- [x] 1.4 Carry `category` and `status` on `VaultNote` in `src/afanes/core/vault.py` and update `_read_note`; add tests for scanned values and invalid category/status handling in `tests/core/test_vault.py`; verify the file passes.
- [x] 1.5 Update `tests/core/test_architecture.py` for the new model and core symbols; verify `hatch test tests/core/test_architecture.py` passes.

## 2. Vault layout and trash

- [x] 2.1 Add public layout constants and the category folder mapping to `src/afanes/core/vault.py`; add `Vault.directory_for` resolving existing case variants and canonical defaults; add tests in `tests/core/test_vault.py`; verify the file passes.
- [x] 2.2 Update `Vault.create` and `Vault.capture` to use layout destinations, remove the `status="inbox"` default, and keep captures statusless; add tests in `tests/core/test_vault.py`; verify the file passes.
- [x] 2.3 Exclude `trash/` case-insensitively from `Vault.scan` and the catalog; add tests for scan exclusion, name reuse, and unresolved references; verify `hatch test tests/core/test_vault.py tests/core/test_links.py` passes.
- [x] 2.4 Replace the public deletion surface with `Vault.plan_trash` and `Vault.trash`, reporting inbound references, requiring confirmation, moving the note to `trash/` with a unique name, and preserving bytes; add tests in `tests/core/test_vault.py`; verify the file passes.
- [x] 2.5 Update `tests/core/test_integration.py` for the new layout and trash path; verify `hatch test tests/core/test_integration.py` passes.
- [x] 2.6 Update `AGENTS.md` sections 3.1 and 4.9 and the `README.md` vault format for the layout, category folders, and trash; verify the documented paths and behavior match the code with `rg`.

## 3. Processing core

- [x] 3.1 Add `src/afanes/core/processing.py` with `ProcessingOutcome` and `ProcessingPlan` value objects, validation, and NumPy-style docstrings; add `tests/core/test_processing.py`; verify the new test file passes.
- [x] 3.2 Add `Vault.plan_processing` to compute destination, metadata, status, category, inbound references, scheme-change warnings, collisions, and content hash; add tests in `tests/core/test_processing.py`; verify the file passes.
- [x] 3.3 Add `Vault.apply_processing` with the content-hash check, atomic write-then-move, retry behavior, collision abort, and body/unknown-key preservation; add tests in `tests/core/test_processing.py`; verify the file passes.
- [x] 3.4 Implement the Trash, Later, Reference, Action, and Project outcomes in the plan/apply path, including action metadata and unresolved references; add tests for every outcome in `tests/core/test_processing.py`; verify the file passes.
- [x] 3.5 Add a capture-to-processing integration test for each outcome, including scan, destination, resolution, and trash/restore checks; verify `hatch test tests/core/test_integration.py` passes.
- [x] 3.6 Update `AGENTS.md` sections 1.3, 1.4, and 3.1 for types, statuses, categories, processing, and the target layout; update the `README.md` processing copy; verify the docs match the specs and code.

## 4. Processing Wizard UI

- [x] 4.1 Add processing-session fields and `plan_processing`, `apply_processing`, and cancel commands to `src/afanes/ui/state.py`, running blocking work off the UI thread; add tests in `tests/ui/test_state.py`; verify the file passes.
- [x] 4.2 Add `src/afanes/ui/views/processing.py` with the decision steps, metadata entry, preview, confirmation, and error banners; centralize copy in `src/afanes/ui/strings.py`; add `tests/ui/test_processing_view.py`; verify the new test file passes.
- [x] 4.3 Add a Process action to `src/afanes/ui/views/inbox.py` and route the wizard through `src/afanes/ui/app.py`; add and update `tests/ui/test_inbox_view.py` and `tests/ui/test_app.py`; verify both files pass.
- [x] 4.4 Verify the source-run application starts without a traceback and the wizard can be opened from a capture; record any environment limitation in the task notes.
- [x] 4.5 Update the `README.md` Inbox and processing usage for the wizard and the new layout; verify the documented commands.

## 5. Integration and quality gates

- [x] 5.1 Run `hatch check` and fix lint, formatting, and type errors; verify the command reports zero errors.
- [x] 5.2 Run `hatch test --cover` and confirm the suite passes with at least 85% overall coverage; verify the coverage summary.
- [x] 5.3 Run `openspec validate --all --strict` and `openspec doctor`; verify zero failures.
- [x] 5.4 Run the neutral-vocabulary compliance check from `AGENTS.md` section 6.6; verify both checks exit clean.
- [x] 5.5 Review the diff for scope, cross-platform behavior, atomic writes, and preserved unknown data; record the review in `design.md` or the change notes.

## Workflow follow-up

- Archive the change after review and the quality gates pass.
- Run the post-archive release workflow in `AGENTS.md` section 5.8. This change removes a public note type and changes the vault format, so the release is a MAJOR bump.
- Update `CHANGELOG.md` and `README.md` as part of the release, and verify the archived specifications.
