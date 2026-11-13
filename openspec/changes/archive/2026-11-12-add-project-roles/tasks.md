# Tasks

## 1. Owner model and label writer

- [x] 1.1 Parse and validate `owner` in `NoteDocument` as one non-empty project-only string, trimming
  on read and rejecting blank, list, or numeric values; verify
  `hatch test tests/core/test_frontmatter.py` passes with owner cases.
- [x] 1.2 Add `owner_text` and `with_owner_text` to `PageLabels`, write `owner` after `asked_by` in
  `apply_to`, and clear it in `with_type`; verify `hatch test tests/core/test_labels.py` passes with
  the label matrix and round-trip cases.
- [x] 1.3 Route the page draft and type-change paths through the updated labels, preserving unknown
  keys and newline style; verify `hatch test tests/core/test_editing.py` passes.
- [x] 1.4 Update `docs/reference/frontmatter.md` and `docs/reference/vault-format.md` with the
  `owner` key, its scope, and the plain-text reference behavior; verify `hatch run docs:build`
  passes.

## 2. Reference plumbing and rename behavior

- [x] 2.1 Add characterization tests for the current rename and trash counts and for step metadata
  preservation, covering body-only references, CRLF, and unknown metadata keys; verify
  `hatch test tests/core/vault/test_naming.py` passes.
- [x] 2.2 Add `owner` and a derived `metadata_references` collection to `VaultNote`, populate them in
  `Vault._read_note`, and update the scan constructors and test helpers; verify
  `hatch test tests/core/vault/test_snapshot.py tests/core/vault/test_service.py` passes.
- [x] 2.3 Count metadata references in `affected_sites` and `plan_reference_repair`, so rename and
  trash previews report projects whose `owner`, `asked_by`, or step `owners` name the target; verify
  `hatch test tests/core/vault/test_naming.py tests/core/vault/test_snapshot.py` passes.
- [x] 2.4 Rewrite `owner`, `asked_by`, and step `owners` in `VaultNaming._rewrite_note` in the same
  atomic write as body references, using `StepDocument.with_owners` to preserve `plan`, `actual`,
  `tags`, unknown keys, and newlines; verify
  `hatch test tests/core/vault/test_naming.py tests/core/vault/test_steps.py` passes.
- [x] 2.5 Extend `_verify_rewrite` and the reference-repair flow to metadata references, including
  skipped and partial-failure paths; verify `hatch test tests/core/vault/test_naming.py` passes.
- [x] 2.6 Update `docs/reference/names-and-links.md` and `docs/reference/step-metadata.md` for
  metadata role references and rename/trash behavior; verify `hatch run docs:build` passes.

## 3. Page display and editing

- [x] 3.1 Add the `Owner` field to the page edit form with `PageEditorState.set_page_owner`. Remove
  the unused `PageEditorState.page_steps` property to keep the controller at its public-name budget,
  keep `set_page_asked_by` in `PageDialogState`, and record the removed property as a public API
  change; verify `hatch test tests/core/test_architecture.py tests/ui/test_state.py tests/ui/test_page_view.py`
  passes.
- [x] 3.2 Show `Owner` before `Asked by` in the project meta row, hide each label when absent, and
  keep the values plain text in the file; verify `hatch test tests/ui/test_page_view.py` passes.
- [x] 3.3 Add vault-name suggestions to the `Owner` and `Asked by` fields while accepting free text;
  verify `hatch test tests/ui/test_page_view.py` passes with suggestion and free-text cases.
- [x] 3.4 Add read-mode owner and requester icons on the project meta row, backed by a shared name
  dialog that saves typed free text as well as a suggestion selection, and save-aware label commands,
  so both roles can be set or cleared without entering edit mode; verify `hatch test
  tests/ui/test_page_view.py tests/ui/test_role_name_dialog.py` passes.
- [x] 3.5 Give the page edit-form controls an explicit height, place every label in one wrapping row,
  and give the edit form the remaining page height through a full-size mode host, with the body and raw
  editors using parent-filling, top-aligned mode instead of line-count minimums, so the Date field
  shares the wide row and the body reaches the bottom; verify `hatch test tests/ui/test_page_view.py`
  passes.
- [x] 3.6 Update `docs/guide/projects-and-steps.md` and `docs/guide/pages-and-editing.md` for the
  Owner field, the header order, and the edit form; verify `hatch run docs:build` passes.

## 4. Connections and search

- [x] 4.1 Add `project_owner_projects` and `finished_project_owner_projects` to `ConnectionSet`
  without renaming the existing step-owned fields, update `has_connections`, and keep the class
  docstring clear about the distinction; verify `hatch test tests/core/test_connections.py` passes.
- [x] 4.2 Index project-level `project_owner_projects` and `finished_project_owner_projects` from
  `owner`, and order them by display title; verify `hatch test tests/core/test_connections.py`
  passes with open, finished, missing, and ambiguous owner cases.
- [x] 4.3 Render the Connections sections in the order Linked from, Owned projects, Owned steps,
  Requested projects, and make the finished-project toggle reveal both finished owned and requested
  projects; verify `hatch test tests/ui/test_page_view.py` passes.
- [x] 4.4 Append `owner`, `asked_by`, and step owner names to the scanned note's search text while
  keeping other metadata out; verify `hatch test tests/core/test_search.py tests/core/vault/test_service.py`
  passes with role-name and metadata-negative cases.
- [x] 4.5 Update `docs/guide/pages-and-editing.md` for Owned projects and the section order, and
  `docs/guide/workspace.md` for role-name search; verify `hatch run docs:build` passes.

## 5. Role navigation and creation

- [x] 5.1 Add `PageNavigator.follow_role` with opened, ambiguous, and missing outcomes, reusing the
  existing page-open and candidate paths; verify `hatch test tests/ui/test_state.py` passes with
  resolved, ambiguous, and missing role names.
- [x] 5.2 Add the shared `RoleReferenceDialog` with an editable category combobox containing `person`,
  every category used by a reference, every reference template category, a free-typed label, and no
  category; verify a new component test and `hatch test tests/ui/test_page_view.py` pass.
- [x] 5.3 Render project owner and requester names and step owner names as role links, keeping the
  chip delete action separate; verify
  `hatch test tests/ui/test_page_view.py tests/ui/test_project_body_view.py` passes.
- [x] 5.4 Add `PageNavigator.create_role_reference` to create the reference atomically, refresh the
  snapshot, and open it for editing, using the matching template card body when one exists, and refresh
  the existing workspace after the dialog closes instead of rebuilding the Flet page; verify creation,
  no-category creation, cancellation, collision, and post-creation Done/Back cases in `hatch test
  tests/ui/test_page_view.py tests/ui/test_app.py`.
- [x] 5.5 Update `docs/guide/pages-and-editing.md` and `docs/reference/names-and-links.md` for
  role-name navigation and creation; verify `hatch run docs:build` passes.

## 6. Processing Wizard

- [x] 6.1 Add `owner` and `asked_by` to `ProcessingPlan`, accept them only for Project and Done now,
  and reject them for other outcomes; verify
  `hatch test tests/core/test_processing.py tests/core/vault/test_processing.py` passes.
- [x] 6.2 Apply the two values through `PageLabels` in `processed_text`, trimming non-blank values
  and removing blank keys; verify the same core processing tests pass with role cases.
- [x] 6.3 Add optional Owner and Asked by fields with suggestions to `ProcessingView`, visible only
  for Project and Done now; verify `hatch test tests/ui/test_processing_view.py` passes.
- [x] 6.4 Pass the fields through `ProcessingState.build_plan` and show them in the plan preview;
  verify `hatch test tests/ui/test_state.py tests/ui/test_processing_view.py` passes.
- [x] 6.5 Update `docs/guide/processing.md` and `docs/getting-started/capture-clarify-review.md` for
  the two role fields; verify `hatch run docs:build` passes.
- [x] 6.6 Update `CHANGELOG.md` under `Unreleased` with the owner, metadata-reference, connections,
  search, and wizard outcomes, naming this change; verify the entry names the change and record the
  README/Docs status.

## 7. Integration verification

- [x] 7.1 Run `hatch check` and verify lint, formatting, and Pyrefly strict pass.
- [x] 7.2 Run `hatch test --cover` and verify the full suite passes at 85% coverage or higher.
- [x] 7.3 Run `hatch run docs:build` and verify the Sphinx build passes with no warnings.
- [x] 7.4 Run `openspec validate --all --strict` and `openspec doctor`, and verify both pass.
- [x] 7.5 Run the two vocabulary/compliance grep commands from `AGENTS.md` section 6.1 and verify
  both exit 1 with no output.
- [x] 7.6 Review the final diff and verify it touches only the files named in the proposal, the
  change artifacts, documentation, and `CHANGELOG.md`, with no unrelated formatting churn.

## Workflow follow-up

- Archive the change after review and implementation are complete.
- Run the post-archive release workflow, record the version decision, README status, and Docs status,
  and report the commit hash.
