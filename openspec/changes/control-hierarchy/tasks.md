# Tasks

## 1. Conformance gate foundation

- [x] 1.1 Add `HEADER_ACTION_KEYS` to `tests/ui/test_conformance.py`, give the page Edit and Done actions explicit keys, and skip exactly those keys in the icon-plus-label rule. Verify the conformance tests pass and a temporary non-header icon-plus-label button is still flagged.
- [x] 1.2 Add a gate test that builds the page toolbar and asserts the allowlist matches the header controls, so the exemption cannot grow without a visible header change. Verify the test passes and fails when a key is removed from the toolbar.
- [x] 1.3 Update the conformance-gate section of `docs/develop/interface-standard.md` to describe the header-bar scope and verify `hatch run docs:build` passes.

## 2. Welcome and page surfaces

- [x] 2.1 Add a visible-control walker and a Welcome test that counts suggested and destructive controls in the built tree. Make Choose Vault (desktop) or Open (browser) the only suggested action and make New Vault an outlined button. Verify `tests/ui/test_inbox_view.py` passes.
- [x] 2.2 Add a page conflict-panel test and keep Reload from Disk as the only suggested action; make Overwrite, Recreate, and Discard regular buttons. Verify `tests/ui/test_page_view.py` passes.
- [x] 2.3 Add a rename and repair panel test; keep Rename and Rewrite Links suggested, and make Preview a regular button. Verify the page view tests pass.
- [x] 2.4 Reorder the inline confirmation panels so Cancel comes first and the affirmative action last: trash, type change, category move, rename, and repair. Add order assertions to `tests/ui/test_page_view.py` and verify they pass.
- [x] 2.5 Make the rename Preview and Rename actions insensitive while the new-name field is blank, with live updates on change. Verify the page view tests cover blank, valid, and cleared states.

## 3. Inbox and processing availability

- [ ] 3.1 Make the Capture action insensitive while the composer is blank or whitespace-only, update it on change, and keep the command-level rejection. Verify `tests/ui/test_workspace_view.py` covers disabled, enabled, cleared, and direct-command cases.
- [ ] 3.2 Make the Processing Preview action insensitive until an outcome is selected and its required project or date is valid. Verify `tests/ui/test_processing_view.py` covers each outcome and the invalid-date case.

## 4. Dialogs and review forms

- [ ] 4.1 Make the New Vault Create action insensitive while the path field is blank, with live updates. Verify the dialog tests in `tests/ui/test_app.py` cover disabled, enabled, and direct-command rejection.
- [ ] 4.2 Make the New Reference Create action insensitive while the name field is blank, with live updates. Verify `tests/ui/test_app.py` covers the dialog and the direct-command rejection.
- [ ] 4.3 Make the Review form Confirm action insensitive until the typed value is non-blank and, for postpone, a valid date. Verify `tests/ui/test_review_view.py` covers add-step, postpone, delegate, and reassign.
- [ ] 4.4 Hide a review card's normal action rows while its inline form or confirmation is open, so only the form's Confirm is suggested; restore the rows on cancel. Verify the review view tests count one suggested action in each open state.

## 5. Icon/label and row density

- [ ] 5.1 Migrate every non-header icon-plus-label button to either an icon or a label, keeping the page toolbar keys exempt. Delete the cleared entries from the `icon_and_label_buttons` baseline and verify the conformance tests pass.
- [ ] 5.2 Remove every remaining `dense=True` row and delete the `dense_rows` baseline entries. Verify the conformance tests pass and the 1024x600 minimum-window test still renders without clipping.

## 6. Integration and documentation

- [ ] 6.1 Mark wave 2 as landed in `docs/develop/interface-standard.md`, describe the insensitive-action, cancel-first, and list-row rules, and refresh the baseline table. Verify `hatch run docs:build` passes and review the affected user guides for statements that changed.
- [ ] 6.2 Run `hatch check`, `hatch test --cover`, `hatch run docs:build`, `openspec validate --all --strict`, `openspec doctor`, and the vocabulary checks. Verify all pass at 85% coverage or higher.
- [ ] 6.3 Check the Welcome, page conflict, rename, review form, and processing surfaces at 1024x600 and 1100x760 in light and dark modes. Verify each surface shows one affirmative style, Cancel comes first, and no control clips.

## Workflow follow-up

- Archive the change after the maintainer's review and the release checks pass.
