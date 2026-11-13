# Tasks

## 1. Log entry outcome

- [x] 1.1 Add `"log": "Log entry"` to `PROCESSING_OUTCOME_LABELS` and `ProcessingOutcome.LOG` to the wizard's ordered outcomes; verify `tests/ui/test_processing_view.py` asserts seven options and the Log entry label.
- [x] 1.2 Add a test that selects Log entry, asserts the project fields and template are hidden, and asserts the preview names Log entry and its destination; verify the test passes.
- [x] 1.3 Verify `docs/guide/processing.md` already documents Log entry and record that no user-facing documentation change is required; verify `hatch run docs:build` passes.

## 2. Connection sections

- [x] 2.1 Render only connection sections with at least one visible row, move both reveal toggles to the Connections panel actions row, and remove the empty-section placeholder strings; verify `tests/ui/test_page_view.py` passes with the updated expectations.
- [x] 2.2 Add view tests for a page with one connection kind (other headings absent), a page with only a finished owned project (section absent, finished-project control visible, enabling reveals it), and a page with only a completed owned step (same pattern); verify the tests pass.
- [x] 2.3 Update `docs/guide/pages-and-editing.md` to describe the footer reveal controls and hidden-only behavior; verify `hatch run docs:build` passes.

## 3. Page starts at the top

- [x] 3.1 Add `PageView.scroll_to_top()` and call it after every page change in browser selection, links, connection entries, owned steps, and Back; verify the page-view and workspace tests pass.
- [x] 3.2 Add tests that each page-change path calls `content.scroll_to` with offset zero, and harden the existing owned-step test to assert both the project title and the scroll reset; verify the tests pass.
- [x] 3.3 Update the affected workspace or page documentation to state that a page change starts at the top; verify `hatch run docs:build` passes.

## 4. Rewrite reports

- [x] 4.1 Add the private rewrite-report formatter on `PageDialogState`, the partial-success strings, and the updated/not-updated/reason wording; use it in rename, type change, date change, and repair; verify the affected UI tests pass.
- [x] 4.2 Add one UI test per rewrite path that simulates a partial failure and asserts the status message names the updated and not-updated notes with relative paths and the reason; verify all four tests pass.
- [x] 4.3 Check whether the user documentation describes partial-failure messages and update it if needed; verify `hatch run docs:build` passes.

## 5. Search and null specifications

- [x] 5.1 Add or adjust a projects-view test so a step-text query lists the project without requiring a matching-step line; verify the test asserts the amended search scenario and passes.
- [x] 5.2 Add parser tests for null `status` and `due_date` on a log, reference, and note; verify each note parses with the value absent.
- [x] 5.3 Update `docs/reference/frontmatter.md` with the null-value rule and fix the `core/frontmatter.py` module docstring from “six” to “seven” recognized keys; verify `hatch run docs:build` passes and the docstring reads seven.

## 6. Core test hardening

- [ ] 6.1 Add the core rename/trash tests for an external rename, a trashed requester, a trashed owner, an unknown frontmatter key, role values after deletion, a trashed step owner, and multiple step owners updating independently; verify each test asserts the post-operation file or connection state.
- [ ] 6.2 Add the processing and log tests for blank role values writing no keys, Append step not inheriting the project owner, and clearing the Log query restoring the tree and calendar; verify each test asserts the outcome rather than a callback.

## 7. UI test hardening

- [ ] 7.1 Add project-overview tests for owner isolation: status, group, next step, the project row, and clearing the owner; verify each test uses an owner-bearing project and asserts the workspace view.
- [ ] 7.2 Strengthen the log-label negative tests by starting from a capture that actually carries `status`, `due_date`, `asked_by`, and `owner`; verify the applied log note omits each key.
- [ ] 7.3 Strengthen the cancellation and read-only tests with vault byte/tree snapshots for rename, role creation, role navigation, repair, and connection reading; verify no file changes on cancel or read.
- [ ] 7.4 Strengthen the suggestion tests with at least two vault names and assert a non-matching name is excluded; verify the filtered list is exact.
- [ ] 7.5 Add an edit-mode test that opens a project with task-list steps and asserts the raw step lines are preserved; verify the test fails if steps are stripped.
- [ ] 7.6 Isolate title matching from body matching and add negative search tests for `actual` and unknown frontmatter metadata; verify the matching cases pass and the metadata cases produce no result.
- [ ] 7.7 Harden the remaining prioritized weak tests for the log owner field, the owner chip delete, the owned-project-only section, non-project outcomes hiding role fields, calendar day accents, and role-name Log search; verify each test asserts the rendered or applied result.

## 8. Gate and integration

- [ ] 8.1 Add `owner` to `LABEL_KEYS` in `tests/core/test_architecture.py`; verify the architecture gate passes and would flag an owner write outside the allowed modules.
- [ ] 8.2 Verify the `RENAMED` deltas for `vault-browsing` and `note-editing` and the modified requirements remain structurally valid and archive-ready; verify `openspec validate --all --strict` passes.
- [ ] 8.3 Run `hatch check`, `hatch test --cover`, `hatch run docs:build`, `openspec doctor`, and both vocabulary compliance greps; verify every command passes.
- [ ] 8.4 Re-run the scenario trace for the six changed capabilities and record the closed findings; verify no changed scenario is left weak or gap.

## Workflow follow-up

- Commit each behavior fix with its regression tests as soon as it is green, then commit the hardening groups separately.
- Archive the change after approval and completion with `openspec archive "restore-workspace-conformance"`.
- Run the post-archive release step: keep the version unchanged unless a milestone completes, add the entries under `Unreleased`, and record the README and docs status.
- Re-run layer 1 and layer 2 after the archive.
- Defer the `vault-browsing` Purpose prose edit to a separate change.
- Do not tag, push, or publish unless asked.
