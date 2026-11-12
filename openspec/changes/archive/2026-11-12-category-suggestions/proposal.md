# Proposal

## Why

The category control in edit mode is a plain text field. Users retype category labels from memory,
which invites duplicates, inconsistent casing, and typos that silently create a new folder group. The
vault already knows every category label in use, so the editor can offer them without taking away the
ability to invent a new one.

## What Changes

- Replace the category text field with an editable combobox that filters as the user types.
- Populate its suggestions from the distinct category labels already present on reference notes in
  the vault, sorted alphabetically and case-insensitively.
- Keep typed free text valid: a label that is not in the list is still accepted and validated by the
  existing category rules.
- Keep the control limited to references, as today.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `note-editing`: edit mode gains a category combobox that suggests existing labels while still
  accepting a new category.

## Impact

- `src/afanes/ui/views/page.py`: the category control becomes an editable filtered dropdown whose
  options are rebuilt from the current browser listing.
- `tests/ui/test_page_view.py`: covers suggestions, filtering, free text, and the reference-only
  visibility.
- `docs/guide/pages-and-editing.md`: documents how to pick or type a category.
- No dependency, vault format, storage, or network impact.
