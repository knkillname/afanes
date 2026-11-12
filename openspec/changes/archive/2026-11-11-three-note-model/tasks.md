# Tasks

## 1. Note model and vocabulary

- [x] 1.1 Reduce `NoteType` to `note`, `reference`, and `project` in `src/afanes/models/note.py`, remove `ReferenceCategory`, add a `CategoryLabel` value object that validates a non-empty single segment and compares case-insensitively, and update the per-type status sets; verify with `hatch test tests/models/test_note.py`.
- [x] 1.2 Reduce `ReferenceScheme` to `project` and `note` in `src/afanes/models/link.py` and make `for_note` independent of category; verify with `hatch test tests/models/test_link.py`.
- [x] 1.3 Add `src/afanes/models/step.py` with frozen `ProjectStep` and `StepMetadata` value objects covering text, checked state, owners, plan, actual, tags, line index, and the preserved raw mapping; verify with new tests in `tests/models/test_step.py`.
- [x] 1.4 Update `src/afanes/core/frontmatter.py` to parse and serialize the four recognized keys, accept a free-form `CategoryLabel`, reject `action`, `person`, `people`, and `project` values, and keep unknown keys preserved; verify with `hatch test tests/core/test_frontmatter.py` including a Hypothesis round-trip.
- [x] 1.5 Update the domain errors and user-facing messages for retired values in `src/afanes/core/errors.py` so an old note reports an actionable reason; verify with `hatch test tests/core/test_errors.py`.

## 2. Step parsing and rewriting

- [x] 2.1 Add `src/afanes/core/steps.py` with a `StepDocument` class that parses a project body through `MarkdownIt("commonmark")`, uses `list_item_open` maps to locate each task item line, and returns `ProjectStep` values; keep every helper a method so the architecture gate passes; verify with new `tests/core/test_steps.py`.
- [x] 2.2 Parse the trailing metadata comment in `StepDocument`: only the last comment on the line, only when the line ends with `-->`, load it with `yaml.safe_load`, normalize dates, and preserve unknown keys; verify with tests for comment placement, prose after the comment, and non-mapping comments.
- [x] 2.3 Add line-level rewriting to `StepDocument` for ticking, unticking, setting a plan date, and replacing owners, preserving the newline style and every other byte; verify with a property test that rewrites round-trip and leave unrelated lines identical.
- [x] 2.4 Apply malformed metadata partially: drop only the invalid key, keep the note readable, and record a file-and-line warning; verify with tests for invalid dates, broken YAML, and an unknown key surviving a tick.
- [x] 2.5 Verify metadata serialization stays on one line and rejects `--` inside a value, producing an actionable warning instead of an invalid comment; cover it in `tests/core/test_steps.py`.

## 3. Scan, catalog, and layout

- [x] 3.1 Extend `VaultNote` in `src/afanes/core/vault.py` with `steps` and `search_text`, and remove `frontmatter_references`; verify with `hatch test tests/core/test_vault.py`.
- [x] 3.2 Derive steps for project notes during the scan, strip metadata comments from `search_text`, and report a `type: note` outside `inbox/` as misplaced; verify with scan tests for a project, a reference with checkboxes, and a misplaced note.
- [x] 3.3 Update `NameCatalog` so all references, categorized or not, resolve through the `note` scheme and projects resolve through `project`; verify resolution, ambiguity, and cross-scheme reuse in `tests/core/test_links.py`.
- [x] 3.4 Update destination selection in `src/afanes/core/vault.py` to map a category label to `reference/<label>/`, fall back to `reference/`, reuse a case variant, and remove `actions/`; verify with folder and case tests in `tests/core/test_vault.py`.

## 4. Processing and apply

- [x] 4.1 Replace the outcome set in `src/afanes/core/processing.py` with `trash`, `later`, `reference`, `project`, `append_step`, and `done_now`; verify each outcome's target type and status in `tests/core/test_processing.py`.
- [x] 4.2 Add an `AppendStepPlan` value object holding the capture, target project, step text, indented detail, and both content hashes, and keep `ProcessingPlan` for single-note outcomes; verify its invariants in `tests/core/test_processing.py`.
- [x] 4.3 Update planning in `src/afanes/core/vault.py` for new projects (including empty ones), done-now projects, and append targets resolved by identity; reject an append target that matches no project; verify each path in `tests/core/test_vault.py`.
- [x] 4.4 Implement append apply as write-project-then-trash, detect an already-present step to avoid duplication on retry, and keep the capture untouched when the project changed; verify success, changed target, and retry in `tests/core/test_processing.py`.
- [x] 4.5 Remove the action creation path and every `actions/` destination from `src/afanes/core/vault.py`; verify the integration tests no longer reference action files and `hatch test tests/core/test_integration.py` passes.

## 5. Projects and browser

- [x] 5.1 Change `ProjectBoard` in `src/afanes/core/search.py` to report open steps and the first unchecked step as the next step; verify ordering by document position, checked steps skipped, owned steps marked waiting, and zero-step projects in `tests/core/test_search.py`.
- [x] 5.2 Change `Browser` sections to Inbox, Projects, References grouped by category label, Needs attention, and Unreadable notes; remove Actions, People, and Notes; verify each group and the misplaced-note listing in `tests/core/test_search.py`.
- [x] 5.3 Make `Browser.filter` match display title, identity, and `search_text`, including step text and excluding metadata comments; verify body-only, step-only, and metadata-only terms in `tests/core/test_search.py`.
- [x] 5.4 Update the workspace view wiring in `src/afanes/ui/state.py` and `src/afanes/ui/views/workspace.py` for the new sections and labels; verify with `hatch test tests/ui/test_workspace_view.py tests/ui/test_state.py`.

## 6. Page editor and references

- [x] 6.1 Update page drafts in `src/afanes/core/editing.py` so `note:` creates an uncategorized reference and `project:` creates a project, with no person case; verify in `tests/core/test_editing.py`.
- [x] 6.2 Replace the label form with type, category, status, and due date, with category limited to references and due date limited to projects; verify each field and the invalid-date block in `tests/ui/test_page_view.py`.
- [x] 6.3 Render project steps as rows in `src/afanes/ui/views/page.py`, hide metadata comments, and wire tick and untick to an atomic line rewrite; verify rendering and the rewritten file in `tests/ui/test_page_view.py`.
- [x] 6.4 Preview and apply the category move when a category changes, then move the file without changing identity or references; verify add, remove, cancel, and move failure in `tests/core/test_editing.py`.
- [x] 6.5 Restrict the type-change preview to moves between `note` and `project` and remove the person example; verify preview, cancel, and the same-scheme path in `tests/core/test_editing.py`.

## 7. Review and digest

- [x] 7.1 Add due-step and waiting-step items to `ReviewPlanner` in `src/afanes/core/search.py` and order the queue as inbox, due, waiting, stalled projects, healthy projects; verify order, closed projects, and the snapshot in `tests/core/test_search.py`.
- [x] 7.2 Change the pending count to include due own steps and waiting steps; verify each contribution and the zero state in `tests/core/test_search.py`.
- [x] 7.3 Add review commands for do it now, postpone, delegate, reassign, open project, and skip in `src/afanes/ui/state.py`; verify each writes only the expected line in `tests/ui/test_state.py`.
- [x] 7.4 Update project review cards to show steps and to add a step to a stalled project's body; verify add, cancel, blank text, done, defer, and skip in `tests/ui/test_review_view.py`.
- [x] 7.5 Add the launch digest of due and overdue own steps that opens the review, with copy in `src/afanes/ui/strings.py`; verify count, activation, empty state, and no write in `tests/ui/test_app.py`.

## 8. CLI and vault creation

- [x] 8.1 Update `src/afanes/cli/vault.py` to seed `inbox/`, `trash/`, `reference/`, and `projects/` and report that list; verify the exact output and the absence of `actions/` in `tests/cli/test_main.py`.
- [x] 8.2 Remove remaining `actions/` references from the CLI and its strings; verify `hatch test tests/cli/test_main.py` and a search for `actions` in `src/afanes/cli`.
- [x] 8.3 Update the `vault create` example output in `README.md` and the CLI help strings; verify the documented command matches the tested output.

## 9. Hard break and documentation

- [x] 9.1 Verify an old vault with `type: action`, `person:` links, and `people`/`project` keys lands in Unreadable notes and opens in raw rescue mode without being rewritten; verify with a fixture vault in `tests/core/test_integration.py`.
- [x] 9.2 Verify a `type: note` outside `inbox/` is listed under Needs attention and cannot be processed; verify in `tests/core/test_integration.py`.
- [x] 9.3 Rewrite the vault format and processing sections of `README.md` for three types, step syntax and schema, category folders, the four seeded folders, and the hard break; verify the documented example parses in a fixture test.
- [x] 9.4 Update `AGENTS.md` sections 1.3, 1.4, 1.5, 4.7, and the vocabulary table for three types, steps, free-form categories, and no person scheme; verify with the compliance search in section 6.6 and a read-through.
- [x] 9.5 Document the step metadata schema in the vault-format section so the vault remains readable outside the app; verify the schema and a round-trip example appear in `README.md`.

## 10. Integration and quality gates

- [x] 10.1 Add an end-to-end test that captures, creates a project, ticks a step, searches for its text, reviews a due step, delegates it, and asserts the resulting files; verify in `tests/core/test_integration.py`.
- [x] 10.2 Run `hatch check` and fix every lint, format, and type finding; verify the command exits zero.
- [x] 10.3 Run `hatch test --cover` and confirm at least 85% coverage with the step parser, link, vault, and indexer modules at 90% or higher; verify the reported percentages.
- [x] 10.4 Run `openspec validate --all --strict` and `openspec doctor`; verify both exit clean.
- [x] 10.5 Run the section 6.6 compliance check and confirm no prohibited vocabulary appears in code, tests, or documentation; verify the check exits without matches.

## Workflow follow-up

- Archive the change after review and the quality gates pass.
- Run the post-archive release workflow in `AGENTS.md` section 5.8: bump to 4.0.0, update `CHANGELOG.md` with the migration note, review `README.md`, and create the release commit.
