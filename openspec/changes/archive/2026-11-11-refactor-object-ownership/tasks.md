# Tasks

## 1. Policy and gate scaffolding

- [x] 1.1 Update `AGENTS.md` with the ownership rule, the six-point decision tree, the four-entry allowlist, and the gate description; verify the new section is present and `openspec validate --all --strict` still passes.
- [x] 1.2 Add `TestObjectOwnership` to `tests/core/test_architecture.py` with a temporary allowlist that names every module not yet migrated; verify `hatch test tests/core/test_architecture.py` passes with the temporary allowlist.
- [x] 1.3 Add the duplicate view-helper assertion and the `AppState` field-budget assertion to the gate, initially covering the current files through the temporary allowlist; verify the gate runs and fails when a temporary duplicate helper is introduced, then remove the temporary violation.
- [x] 1.4 Record the migration order and the shrinking-allowlist rule in the gate module docstring; verify the docstring names the four final allowlist entries.

## 2. Model and leaf value objects

- [x] 2.1 Move `allowed_statuses` to `NoteType.allowed_statuses` and update `processing.py`, `editing.py`, `vault.py`, `ui/views/page.py`, and their tests; verify `hatch test tests/models/test_note.py tests/core/test_processing.py tests/core/test_editing.py tests/core/test_vault.py` passes.
- [x] 2.2 Move `scheme_for_note` to `ReferenceScheme.for_note` and update `links.py`, `vault.py`, `editing.py`, and their tests; verify `hatch test tests/core/test_links.py tests/core/test_vault.py tests/core/test_editing.py` passes.
- [x] 2.3 Add `ReferenceKey` with `from_reference`, replace `links.reference_key`, and update `frontmatter.py`, `links.py`, `vault.py`, and tests; verify `hatch test tests/core/test_links.py tests/core/test_frontmatter.py tests/core/test_vault.py` passes.
- [x] 2.4 Add `NoteOrder` and replace the three sort-key tuples in `vault.py` and `search.py`; verify `hatch test tests/core/test_search.py tests/core/test_vault.py` passes and ordering outcomes are unchanged.
- [x] 2.5 Add `MarkdownRewrite`, `LinkLabel`, `EditBatch`, and `CatalogEntry`, and update the `links.py` call sites and tests; verify `hatch test tests/core/test_links.py` passes.
- [x] 2.6 Add `FrontmatterSplit`, move `_split_frontmatter` into `NoteDocument` as a private method, and update the tests; verify `hatch test tests/core/test_frontmatter.py` passes.
- [x] 2.7 Add `ProcessingTarget` with `from_outcome`, move `_processing_target` into it, and update `ProcessingPlan`, `Vault`, and tests; verify `hatch test tests/core/test_processing.py tests/core/test_vault.py` passes.
- [x] 2.8 Add `DueDateText`, move `parse_due_date` and `due_date_text_from_raw` into it, and update `PageLabels` and tests; verify `hatch test tests/core/test_editing.py tests/ui/test_page_view.py` passes.
- [x] 2.9 Remove the group-2 modules from the temporary allowlist; verify `hatch test tests/core/test_architecture.py` passes with the reduced allowlist.

## 3. Markdown and vault ownership

- [x] 3.1 Add `MarkdownBody` and move the rewriting helpers into private methods; update `Vault` and the link tests; verify `hatch test tests/core/test_links.py tests/core/test_vault.py` passes with the same rewrite outcomes.
- [x] 3.2 Add `ReferenceParser` and `DestinationKind.classify`, replace the remaining free parsing functions, and update the call sites and tests; verify `hatch test tests/core/test_links.py tests/core/test_frontmatter.py` passes.
- [x] 3.3 Move the `Vault` construction, scan, note-path, and read-note helpers into `Vault`; verify `hatch test tests/core/test_vault.py tests/core/test_integration.py` passes.
- [x] 3.4 Move the `Vault` processing, creation, and rewrite helpers into `Vault`; verify `hatch test tests/core/test_vault.py tests/core/test_processing.py` passes.
- [x] 3.5 Move `_find_note`, `_affected_sites`, `_resolves_to`, and `_hash_for_note` into `VaultSnapshot`; verify `hatch test tests/core/test_vault.py tests/core/test_search.py` passes.
- [x] 3.6 Move `is_open_project` and `is_open_action` to `VaultNote` and update `search.py` and tests; verify `hatch test tests/core/test_search.py` passes.
- [x] 3.7 Remove the group-3 modules from the temporary allowlist; verify `hatch test tests/core/test_architecture.py` passes with the reduced allowlist.

## 4. Page and draft unions

- [x] 4.1 Add `PageFile`, `ParsedPage`, and `UnparsedPage`; change `Vault.read_page` to return the union and update the tests; verify `hatch test tests/core/test_vault.py` passes and invalid page states cannot be constructed.
- [x] 4.2 Add `DraftCommon`, `NormalDraft`, and `RawDraft`; move the draft factories and mode-specific methods; verify `hatch test tests/core/test_editing.py` passes and `NormalDraft`/`RawDraft` expose the expected shared properties.
- [x] 4.3 Update `AppState` and the page view to use the union and the facade page properties; verify `hatch test tests/ui/test_state.py tests/ui/test_page_view.py` passes.
- [x] 4.4 Remove the group-4 modules from the temporary allowlist; verify `hatch test tests/core/test_architecture.py` passes with the reduced allowlist.

## 5. Query services

- [x] 5.1 Add `Browser` and move `browse_groups`, `filter_notes`, `_section_for`, and `_sorted_notes` into it; update `AppState` and the tests; verify `hatch test tests/core/test_search.py tests/ui/test_state.py` passes.
- [x] 5.2 Add `ProjectBoard` and move `project_summaries`, `project_groups`, `_attributed_projects`, `_project_summary`, `_project_sort_key`, `_action_sort_key`, and `_project_stage` into it; verify `hatch test tests/core/test_search.py tests/ui/test_state.py` passes.
- [x] 5.3 Add `ReviewPlanner` and move `review_queue` and `review_pending_count` into it; verify `hatch test tests/core/test_search.py tests/ui/test_state.py` passes.
- [x] 5.4 Rewrite `tests/core/test_search.py` around the three services and keep the existing outcome assertions; verify the rewritten test file passes.
- [x] 5.5 Remove `search.py` from the temporary allowlist; verify `hatch test tests/core/test_architecture.py` passes with the reduced allowlist.

## 6. Shared UI components

- [x] 6.1 Add the `Banner` component and replace the five `_banner` copies; verify `hatch test tests/ui/test_inbox_view.py tests/ui/test_page_view.py tests/ui/test_processing_view.py tests/ui/test_review_view.py tests/ui/test_workspace_view.py` passes.
- [x] 6.2 Add the `StatusLabel` component and replace the two `_status_label` copies; verify the Projects and Review view tests pass.
- [x] 6.3 Add the `Panel` and `Card` components and replace the local `_panel` and `_card` helpers; verify the Page and Review view tests pass.
- [x] 6.4 Replace the `build_*` view functions with classmethods or direct `View(...).build()` construction and update `ui/app.py`; verify `hatch test tests/ui/` passes.
- [x] 6.5 Remove `ui/views` and the shared-component exceptions from the temporary allowlist; verify `hatch test tests/core/test_architecture.py` passes with the reduced allowlist.

## 7. AppState facade and collaborators

- [x] 7.1 Add `VaultSession` and move the vault lifecycle, snapshot, notes, failures, capture, open/change vault, and session gating into it; verify the vault/session subset of `tests/ui/test_state.py` passes.
- [x] 7.2 Add `BrowserState` and move the active section, browser query, and browser listing into it; verify the browser subset of `tests/ui/test_state.py` passes.
- [x] 7.3 Add `PageEditorState` and move the page union, editing mode, history, conflict, ambiguity, pending labels, type-change sites, and the repair/rename/trash previews into it; verify the page-editing subset of `tests/ui/test_state.py` passes.
- [x] 7.4 Move page save, autosave, reload, overwrite, recreate, discard, link navigation, and candidate selection into `PageEditorState`; verify the page lifecycle subset of `tests/ui/test_state.py` passes.
- [x] 7.5 Add `ProcessingState` and move the processing note, body, plan, result, and commands into it; verify the processing subset of `tests/ui/test_state.py` passes.
- [x] 7.6 Add `ReviewState` and move the review session and review commands into it; verify the review subset of `tests/ui/test_state.py` passes.
- [x] 7.7 Make `AppState` a facade over the five collaborators with delegation and the shared lock; verify all `tests/ui/test_state.py` tests pass and views still use `afanes.ui.state.app_state`.
- [x] 7.8 Remove `state.py` from the temporary allowlist and enforce the ten-field budget; verify `hatch test tests/core/test_architecture.py` passes.

## 8. Remaining public functions and final policy

- [x] 8.1 Move `parse_launch_options`, `_require_runtime`, `_checked_vault`, and `_fail` into `LaunchOptions` or a `Launcher` service; verify `hatch test tests/ui/test_launch.py` passes.
- [x] 8.2 Move `open_vault` into a `VaultOpener` service and update `AppState` and `__main__`; verify the vault-opening tests in `tests/ui/test_state.py` and `tests/ui/test_launch.py` pass.
- [x] 8.3 Move `config_directory` and `settings_path` into `SettingsStore` classmethods and update the tests; verify `hatch test tests/core/test_settings.py` passes.
- [x] 8.4 Remove every temporary allowlist entry and assert that the final allowlist is exactly `core/names.py`, `core/atomic.py`, `ui/strings.py`, and the `__main__.py`/`ui/app.py` entry points; verify `hatch test tests/core/test_architecture.py` passes.
- [x] 8.5 Update `AGENTS.md` with the final allowlist, the gate behavior, and the migration note requirements; verify the document and `openspec validate --all --strict` pass.

## 9. Integration verification

- [x] 9.1 Run `hatch check` and verify Ruff and Pyrefly pass.
- [x] 9.2 Run `hatch test --cover` and verify at least 85% overall coverage and at least 90% for the parser, link, and vault modules.
- [x] 9.3 Run `openspec validate --all --strict` and `openspec doctor`; verify both pass.
- [x] 9.4 Run the vocabulary compliance check from `AGENTS.md` section 6.6 and verify no prohibited vocabulary remains.
- [x] 9.5 Review the path, file-write, and UI changes for macOS, Linux, and Windows behavior; record the review result.
- [x] 9.6 Run the integration suite and a manual smoke test covering capture, process, open, edit, autosave, conflict recovery, review, rename, trash, and repair; verify user-visible behavior is unchanged.

## Verification record

- `hatch check`: passed (Ruff lint, Ruff format, Pyrefly strict).
- `hatch test --cover`: 847 passed; 89% total coverage; frontmatter 97%, links 94%, vault 90%.
- `openspec validate --all --strict`: 13 passed, 0 failed.
- `openspec doctor`: root ok, no broken references.
- Vocabulary compliance: the section 6.6 grep returned no matches.
- Cross-platform review: no OS-specific branches were introduced; all paths use `pathlib`, case-insensitive directory reuse is preserved, and atomic writes still go through `core/atomic.py`. Windows reserved names and case-insensitive collisions remain covered by the existing name tests.
- Workflow smoke coverage: `tests/core/test_integration.py`, `tests/ui/test_state.py`, and `tests/ui/test_app.py` exercise capture, processing, page open/edit/autosave, conflict recovery, review, rename, trash, and repair. A rendered Flutter window was not available in this environment; the presentation-facing tests use the same controller commands and controls without a live display.

## Workflow follow-up

- Archive the change after implementation and review are complete.
- Run the post-archive release workflow: bump with `hatch version major` to `3.0.0`, write the changelog entry and migration note, review `README.md`, run all gates, and create the `chore(release): v3.0.0` commit with `Archived OpenSpec change: refactor-object-ownership` in the body.
- Report the previous and new versions, the migration note, the README decision, and the release commit hash.
