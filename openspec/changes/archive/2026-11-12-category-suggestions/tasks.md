# Tasks

## 1. Category combobox

- [x] 1.1 Replace `PageView.category_field` with an editable, filtered `ft.Dropdown` at the existing label width and keep `on_select` wired to `change_category`; verify `hatch run pytest tests/ui/test_page_view.py` passes.
- [x] 1.2 Add a private `_category_options()` helper that collects and sorts the reference category labels from `state.browser.listing()` and call it from `_refresh_edit`; verify the options update when the vault snapshot changes.
- [x] 1.3 Add page-view tests for the suggestions (existing labels, case-insensitive filtering, a typed new label, and no labels yet) and confirm the control stays hidden for non-references; verify `hatch run pytest tests/ui/test_page_view.py` passes.

## 2. Documentation and verification

- [x] 2.1 Document picking or typing a category in `docs/guide/pages-and-editing.md`; verify `hatch run docs:build` passes.
- [x] 2.2 Verify in a live window that typing filters the menu and that Enter commits an unlisted label; if free text does not commit, switch to the text-field-with-suggestions fallback recorded in `design.md` and update the task list.
- [x] 2.3 Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, and `openspec doctor`; verify all pass before reporting the change complete.
