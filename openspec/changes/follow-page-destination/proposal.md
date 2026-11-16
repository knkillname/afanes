# Proposal

## Why

The navigation sidebar and browser currently track the destination the user was browsing, not the note
that is open. Opening a project, then selecting its owner, shows the owner’s reference in the detail
region while the sidebar and browser still show Projects. The Review flow already selects the opened
note’s destination, so the same action behaves differently depending on where it starts.

## What Changes

- Any page opened by navigation — a body link, role name, connection entry, ambiguous-reference
  candidate, or search result — selects the note’s home destination in the navigation and browser.
- Back restores the destination of the page it returns to, not only the page.
- Selecting a search result leaves search mode and shows the result’s home destination.
- Selecting a destination in the sidebar still keeps the open page, as today. The sidebar then
  reflects the browser the reader chose, not the page.
- Trashed pages select Trash. Unreadable notes keep the current destination because they have no
  browser group.
- The Review flow reuses the same destination mapping instead of duplicating it.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `vault-browsing`: page navigation selects the opened note’s home destination; search result
  selection leaves search; Back restores the previous page’s destination; manual destination
  selection continues to keep the open page.

## Impact

- `src/afanes/ui/state/browser.py`: owns the note-to-destination mapping and the navigation selection.
- `src/afanes/ui/state/navigation.py`: updates the destination after opening a page, following a
  link or role name, choosing a candidate, and going Back.
- `src/afanes/ui/state/review.py`: replaces its local mapping with the shared behavior.
- `src/afanes/ui/views/workspace.py` and `src/afanes/ui/views/page.py`: existing refresh paths carry
  the changed destination to the visible controls; no new file I/O.
- `docs/guide/workspace.md` and `docs/guide/pages-and-editing.md`: document the navigation rule.
- Tests: UI state and workspace coverage for links, roles, connections, search results, Back,
  manual destination changes, Trash, and unreadable notes.
- No vault format, CLI, dependency, or persistence change. No runtime network access.
