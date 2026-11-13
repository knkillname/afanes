# Tasks

## 1. Browser search row

- [x] 1.1 Add the search-mode copy in `src/afanes/ui/strings.py`: a `BROWSER_SEARCH_TITLE` value of `Search results`, a `BROWSER_SEARCH_CLEAR` tooltip, and a `BROWSER_SEARCH_HINT` of `Search all notes…`; verify the workspace references each constant and the focused workspace search tests pass.
- [x] 1.2 Restructure `WorkspaceView` so `browser_header` holds only the navigation toggle, destination title, refresh, and destination actions, and add a `browser_search_bar` row beneath it containing `search_field` and a clear button; verify a layout test finds the search field in the search row and not in the header row.
- [x] 1.3 Give `browser_title` room to expand and keep the existing `HEADER_HEIGHT`/spacing tokens; verify the wide and narrow workspace layout tests still pass and the search row remains attached to the header.
- [x] 1.4 Implement the clear action through `BrowserState.set_query("")` and keep the clear button visible only while the query is non-empty; verify clicking it clears the query, restores the destination title, and refreshes the browser list.

## 2. Search mode behavior

- [x] 2.1 Add one `searching` predicate based on `BrowserState.query.strip()` and use it to switch the browser title to `Search results` while a query is active; verify typing a query changes the title and clearing it restores the destination title.
- [x] 2.2 Hide the Inbox capture composer, References New Reference action, Review queue, and Log date-lens controls while `searching`; verify each destination renders its controls normally with an empty query and omits them with a non-empty query.
- [x] 2.3 Remove the `active_section is LOG` branch from `_search_controls()` so every search shows the same grouped result list regardless of the origin destination, while Log matches still come from the query-filtered timeline; verify a search started in Log shows grouped results without the calendar or date tree, and the same query from Inbox shows the same sections.
- [x] 2.4 Route `Escape` through a new `WorkspaceView.clear_search()` command before the existing drawer close; verify `Esc` clears a non-empty query and that `Esc` with an empty query still closes the navigation drawer.
- [x] 2.5 Keep `Ctrl+F` focused on the permanent search field and update the existing keyboard test if its assumptions change; verify `Ctrl+F` reaches the search field from another destination.

## 3. Documentation

- [x] 3.1 Update `docs/guide/workspace.md` to describe the dedicated search row, the `Search results` title, hidden destination controls, and the no-sidebar-search rule; verify the prose matches the implemented behavior and links remain valid.
- [x] 3.2 Update `docs/develop/interface-standard.md` so the browser header owns the destination title and actions, and the search row owns the global search entry; verify `hatch run docs:build` passes with warnings treated as errors.

## 4. Integration verification

- [x] 4.1 Run `hatch check` and fix any lint, format, or type failures introduced by the change.
- [x] 4.2 Run `hatch test --cover` and confirm coverage remains at or above the project minimum.
- [x] 4.3 Run `openspec validate --all --strict` and `openspec doctor`, and confirm the change validates cleanly.

## Workflow follow-up

- Archive the change after the project review requirements are satisfied and the implementation tasks are complete.
- Follow the post-archive release workflow in `AGENTS.md` section 5.3, including changelog, docs, and README status.
