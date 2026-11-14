# Tasks

## 1. Default date title

- [x] 1.1 Add the `LogTitle` value object to `src/afanes/core/log.py` with `for_date` and `text` for day, month, and year precision; verify `tests/core/test_log.py` covers `November 13, 2026`, `November 2026`, `2026`, and a single-digit day, then run `hatch test tests/core/test_log.py`.

## 2. Core log draft creation

- [x] 2.1 Add `NormalDraft.for_log(date, title)` in `src/afanes/core/editing.py` with the ISO identity, `type: log`, the matching `date`, and a `# <title>` body; verify `tests/core/test_editing.py` covers the type, date, identity, heading, and title editing, then run `hatch test tests/core/test_editing.py`.
- [x] 2.2 Replace `VaultPages.create_log_entry` with `VaultPages.create_log_page(date, text)` in `src/afanes/core/vault/pages.py`, validating the exact draft text, log type, matching date, nonblank title, collision, and containment before an atomic write; verify `tests/core/vault/test_pages.py` covers day, month, year, exact text, malformed input, occupied date, and path containment, then run `hatch test tests/core/vault/test_pages.py`.

## 3. Draft lifecycle and first write

- [x] 3.1 Add `PageEditorState.start_log_draft(date, listing)` and `PageNavigator.start_log_draft` with the existing commit, history, and command-lock behavior; verify `tests/ui/test_state.py` covers opening a draft, committing the previous draft, and history, then run `hatch test tests/ui/test_state.py`.
- [x] 3.2 Add the `NoteType.LOG` branch to `PageEditorState._create_new_page` so the exact draft text is written at the date path and an untouched draft is discarded; verify `tests/ui/test_state.py` covers first content, untouched draft, starter selection as content, and an occupied date, then run `hatch test tests/ui/test_state.py`.
- [x] 3.3 Run `hatch test tests/core/test_architecture.py` and confirm the added state fields and commands stay within the controller budget.

## 4. Direct routing and dialog removal

- [x] 4.1 Replace `AppShell.show_log_entry_dialog` with a handler that opens an occupied date through `open_page` and an empty date through `start_log_draft`; verify `tests/ui/test_app.py` covers both paths and no dialog, then run `hatch test tests/ui/test_app.py`.
- [x] 4.2 Route the empty calendar day, **Today's Entry**, and the month/year plus controls through the new handler while keeping an occupied day in read mode and a multi-entry day in tree expansion; verify `tests/ui/test_workspace_view.py` covers all five paths, then run `hatch test tests/ui/test_workspace_view.py`.
- [x] 4.3 Remove the now-unused `Navigation.open_or_create_log_entry` creation command and update its tests; verify `tests/ui/test_state.py` covers the replacement draft path and no immediate write, then run `hatch test tests/ui/test_state.py`.
- [x] 4.4 Update `docs/guide/log.md`, `docs/guide/workspace.md`, and the bundled `src/afanes/templates/_guide/en/reference/Getting started.md` for direct drafts, read-mode occupied dates, and the absence of the dialog; verify the documented sequence matches the implemented paths.

## 5. Starter control

- [x] 5.1 Add a `LogDraftStarter` value object and the page-state fields and commands that hold the card listing, selected card, and generated body; verify `tests/ui/test_state.py` covers selection, Empty, visibility after content, and an existing entry, then run `hatch test tests/ui/test_state.py`.
- [x] 5.2 Add the `TemplateCardContext.LOG` picker above the body field in edit mode, visible only while the draft is a new log draft with no content beyond its generated body; verify `tests/ui/test_page_view.py` covers visibility, selection, Empty, invalid-card warning, and an existing entry, then run `hatch test tests/ui/test_page_view.py`.
- [x] 5.3 Update `docs/reference/template-cards.md` and `docs/guide/pages-and-editing.md` for the Starter control and the log draft rule; verify the card examples and creation sequence match the implemented behavior.
- [x] 5.4 Run `hatch test tests/core/test_architecture.py` and confirm the new page-state surface stays within the controller budget.

## 6. Date-change heading

- [x] 6.1 Add `RenamePreview.new_heading` and apply it during `_write_conversion` in `src/afanes/core/vault/naming.py` so a conversion can replace the heading in the same atomic write; verify `tests/core/vault/test_naming.py` covers the new field and the conversion write, then run `hatch test tests/core/vault/test_naming.py`.
- [x] 6.2 Update `LogConversions.plan_log_date_change` to compare the current title with `LogTitle.for_date(note.date).text` and set the new heading only on a match; verify `tests/core/vault/test_naming.py` covers the generated day, month, year, precision change, custom title, and date-shaped custom title, then run `hatch test tests/core/vault/test_naming.py`.
- [x] 6.3 Commit a dirty log draft before planning its date change so the preview sees the current body; verify `tests/ui/test_state.py` covers a dirty draft date change and preserves the content, then run `hatch test tests/ui/test_state.py`.
- [x] 6.4 Update the date-change paragraph in `docs/guide/log.md` and the relevant page-editing text for the generated-heading rule; verify the examples match the implemented comparison.

## 7. Copy and release notes

- [x] 7.1 Remove the unused log dialog strings, rename the first-write notice to describe writing, and update the copy-gate classifications; verify `hatch test tests/ui/test_copy.py` passes.
- [x] 7.2 Update `CHANGELOG.md` under `Unreleased` with the direct draft, read-mode occupied date, Starter control, default title, date-change heading rule, and the `create_log_entry` replacement; verify the entry names observable outcomes and the replacement API.
- [x] 7.3 Review `README.md` and the remaining `docs/` pages for stale dialog or creation wording and record `README: no change required` when unchanged; verify `hatch run docs:build` passes.

## 8. Integration checks

- [x] 8.1 Run `hatch check` and confirm Ruff, formatting, and Pyrefly pass.
- [x] 8.2 Run `hatch test --cover` and confirm every test passes at 85% coverage or higher.
- [x] 8.3 Run `openspec validate --all --strict` and `openspec doctor`.
- [x] 8.4 Run both vocabulary scans and `git diff --check`.
- [x] 8.5 Review the final diff for scope, cross-platform parity, and preserved atomic-write and path-containment rules.

## Workflow follow-up

- Manually review the Log in a desktop session: click an empty day, choose a starter, leave an untouched draft, open an occupied day, and change a generated date title.
- Archive the change after the review requirements are satisfied.
- Run the post-archive release step in `AGENTS.md` section 5.3; this change is expected to stay under `Unreleased` unless the archive completes a larger milestone.
