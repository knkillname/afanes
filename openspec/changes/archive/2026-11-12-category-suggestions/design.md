# Design

## Context

See `proposal.md` for motivation and `specs/note-editing/spec.md` for the behavior contract.

Edit mode builds `category_field` as an `ft.TextField` in `ui/views/page.py` and refreshes it from
the page draft labels. The vault already exposes category labels through the browser listing:
`state.browser.listing()` returns groups for `BrowserSection.REFERENCES`, and each group carries its
`CategoryLabel` (or `None` for uncategorized references). The view already reads this listing shape
elsewhere, so no new state or query is required.

Flet 1.1.2 has no `Autocomplete` control. `ft.Dropdown` supports `editable=True` (free text) and
`enable_filter=True` (case-insensitive filtering) with `on_select`, which is the native combobox
shape this feature needs.

## Goals / Non-Goals

**Goals:**

- One control that both filters existing labels and accepts an unlisted label.
- Suggestions reflect the vault without adding state, persistence, or a new dependency.
- Keep the existing category validation, move preview, and reference-only visibility untouched.

**Non-Goals:**

- Managing categories globally (rename, merge, delete).
- Reordering or grouping categories by usage.
- Changing the vault folder layout or the category move rules.

## Decisions

### Decision: use the editable, filtered dropdown

`category_field` becomes
`ft.Dropdown(editable=True, enable_filter=True, on_select=self.change_category)` with the same
`PAGE_FIELD_WIDTH` as the other label fields. Selecting an option and typing a new label both submit
through the existing `change_category` command, so validation and the folder-move preview stay in one
place.

Alternative considered: a separate suggestions button next to a text field. It keeps typing behavior
unchanged but is not a combobox, and it adds a second interaction target to a small form row.

### Decision: derive suggestions from the browser listing

A private `_category_options()` helper reads `state.browser.listing()`, collects
`group.label.value` for the reference groups, de-duplicates, and sorts case-insensitively. The helper
is called from `_refresh_edit` so the option list follows the scan as new categories appear. No
controller, `AppState` field, or persisted preference is added.

Alternative considered: deriving labels directly from `state.session.snapshot.notes`. That repeats
the filtering and grouping rules the browser already owns, so the listing is the narrower source.

### Decision: keep the current validation and commit path

Typing a label and submitting reuses `change_category`: blank means uncategorized, an invalid label
shows `PAGE_CATEGORY_INVALID` and blocks the update, and a valid new label goes through
`set_page_category` and its move preview. A blur handler commits typed text when the field loses
focus, so a label is not lost if the user never presses Enter; it is skipped while a move preview is
already waiting. The control stays hidden for notes and projects.

## Risks / Trade-offs

- **Editable dropdown submission semantics** → typing a value and pressing Enter should call
  `on_select`; if the running Flet build does not commit free text that way, the fallback is a text
  field plus a suggestions menu. The apply task verifies typing, selecting, and filtering in a live
  window before the change is accepted.
- **Stale suggestions between scans** → the options refresh with the edit form and the background
  refresh loop keeps the snapshot current; a category created in another program appears at the next
  scan, which is the same freshness the browser already has.
- **Long labels in a narrow field** → the field keeps `PAGE_FIELD_WIDTH`; text truncates in the
  closed control while the menu shows full labels. Widening the row is out of scope.
- **Case variants** → suggestions come from the labels as written in the vault, so `Person` and
  `person` can appear separately. Normalizing case would change existing folder behavior and is out
  of scope.
