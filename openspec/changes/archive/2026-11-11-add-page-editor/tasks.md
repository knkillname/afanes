# Tasks

## 1. Vault page I/O

- [x] 1.1 Add `ContentChangedError` and a `PageContent` value object, and implement `Vault.read_page` returning the raw text, content hash, parsed document, and parse failure; verify with `tests/core/test_vault.py` cases for a normal note, a malformed note, a missing path, and a path outside the vault.
- [x] 1.2 Implement `Vault.write_page` with the expected-hash guard, atomic write, newline preservation, and returned new hash; verify success, conflict, and containment tests in `tests/core/test_vault.py`.
- [x] 1.3 Implement `Vault.create_page` with exact sanitized identity, scheme and directory collision checks, and no numeric suffix; verify exact creation, same-scheme collision, case-insensitive sibling collision, and directory creation in `tests/core/test_vault.py`.
- [x] 1.4 Add `VaultSnapshot.link_target` with resolved, ambiguous, missing, and broken outcomes, including normalized-stem failure matching; verify every outcome and a multi-failure picker case in `tests/core/test_vault.py` or `tests/core/test_links.py`.
- [x] 1.5 Expose `VaultSnapshot.referrers` and add `Vault.plan_reference_repair` / `Vault.apply_reference_repair` with equality matching, captured hashes, skipped changed files, and a rewrite report; verify with `tests/core/test_vault.py` cases for multiple referring notes, a custom label, a skipped note, and an unresolved safe name.
- [x] 1.6 Add `core/editing.py` with the frozen `PageDraft` value object: load from `PageContent`, template baseline, dirty detection, body and label transformations, scheme derivation, due-date normalization from YAML date or ISO string, and raw-to-normal upgrade; verify pure behavior in `tests/core/test_editing.py`.

## 2. Rename heading rule

- [x] 2.1 Extend `RenamePreview` and `plan_rename` to record whether the first level-1 heading matches the old identity and needs updating; verify the flag in `tests/core/test_vault.py` for a matching heading, a custom heading, a missing heading, and a heading inside a code block.
- [x] 2.2 Apply the heading update in `apply_rename` with the same content-hash guard and re-run safety as reference rewrites, and report a skipped or failed heading update; verify default, custom, missing, skipped, and re-run cases in `tests/core/test_vault.py`.

## 3. Application state

- [x] 3.1 Add the page draft, page mode, conflict state, and bounded history to `AppState`, with `open_page`, `back`, `edit_page`, and `done_editing` commands and reset coverage; verify read mode, history order, oldest-entry clearing, the 50-entry cap, and untouched-draft discard in `tests/ui/test_state.py`.
- [x] 3.2 Add draft body and label commands, type-aware status/category rules, assignment suggestions, and the scheme-change preview/confirm flow with a refreshed snapshot; verify state behavior in `tests/ui/test_state.py`.
- [x] 3.3 Add the autosave command and commit paths for Done, Back, and navigation, including conflict states for reload, overwrite, recreate, and discard; verify with patched `Vault` collaborators and controlled timing in `tests/ui/test_state.py`.
- [x] 3.4 Add link routing over `VaultSnapshot.link_target`: resolved opens, ambiguous exposes candidates, missing creates the correct draft, broken routes to rescue, unsafe names plan the repair, and external destinations are inert; verify each branch in `tests/ui/test_state.py`.
- [x] 3.5 Add page-level rename and trash integration, including preview retention, confirmed apply, path/history updates, and return to the previous page; verify in `tests/ui/test_state.py`.
- [x] 3.6 Add failure lookup and raw rescue state, including opening a broken note from a link or the failure list and upgrading after a successful parse; verify in `tests/ui/test_state.py`.

## 4. Page view

- [x] 4.1 Build the read mode header and body in `ui/views/page.py` with Back, title, path, Edit/Done, action menu, and an `ft.Markdown` link callback; verify controls and link forwarding in `tests/ui/test_page_view.py`.
- [x] 4.2 Build the edit mode raw body field, label form, status/category gating, due-date inline error, and people/project suggestion lists; verify rendering and state calls in `tests/ui/test_page_view.py`.
- [x] 4.3 Build raw rescue mode with the warning, no label form, and a save action; verify the control states in `tests/ui/test_page_view.py`.
- [x] 4.4 Build the conflict banner, ambiguity picker, reference-repair dialog, and type-change confirmation; verify each renders the required choices and calls the matching command in `tests/ui/test_page_view.py`.
- [x] 4.5 Replace the Inbox preview pane with the page view, wire the shell and reset behavior, and make failure-banner paths open rescue mode; verify existing Inbox tests still pass and add coverage in `tests/ui/test_inbox_view.py`.
- [x] 4.6 Add all page copy to `ui/strings.py`, sizing to `ui/theme.py`, and accessibility labels for the new controls; verify with `hatch check` and the page view tests.

## 5. Integration and documentation

- [x] 5.1 Add an integration test that opens an Inbox capture, follows a resolved link, creates a page from an unresolved link, edits its body and labels, and verifies the files and scan result in `tests/core/test_integration.py`.
- [x] 5.2 Add integration coverage for a conflict, raw rescue, rename, and trash through the state commands, using a fixture vault; verify in `tests/ui/test_state.py` or `tests/core/test_integration.py`.
- [x] 5.3 Review and update `README.md` for reading, link navigation, page creation, editing, autosave, raw rescue, rename, and trash; verify the documented workflows match the implemented commands.
- [x] 5.4 Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, `openspec doctor`, and the vocabulary compliance check; fix every failure before reporting the change complete.

## Workflow follow-up

- Archive the change with the project archive workflow after review and validation.
- Run the post-archive release workflow from AGENTS.md section 5.8, including the version bump, `CHANGELOG.md`, the final `README.md` review, the full gates, and the release commit.
