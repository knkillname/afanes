# Design

## Context

See `proposal.md` for the motivation. The current workspace has three regions: navigation, browser, and detail. `WorkspaceView` builds one 48 px browser header containing the navigation toggle, the destination title, the permanent search field, refresh, and the active destination's actions. `BrowserState.query` is the only search state; `WorkspaceView._refresh_dynamic()` rebuilds the browser from `BrowserState.listing()`, and `_browser_controls()` switches to `_search_controls()` whenever the query is non-empty.

The browser column is 320–360 px wide. Putting the title, search field, refresh, and actions in one row leaves the field cramped and makes the destination title read as the search field's label. Search results are already global, but the title and destination controls do not fully switch to a search mode: the Inbox composer and References action can remain visible, and `_search_controls()` has a Log-only branch that appends the Log calendar and date tree.

The HIG guidance that shapes this design:

- A sidebar contains locations; search is a global content filter, not a location.
- The standard search pattern is a search bar beneath the header, and a permanent search entry is permitted when search is particularly important.
- Header content should update with the current mode.
- Search results belong in the content view and should be global and predictable.

## Goals / Non-Goals

**Goals:**

- Give the global search entry its own full-width row beneath the browser header.
- Make the browser header contain only the destination title and destination actions.
- Make search mode explicit with a **Search results** title and one origin-independent result list.
- Hide destination-specific browser content while a query is active.
- Keep the sidebar as a destinations-only list and keep the existing search matching and query lifecycle.
- Preserve keyboard access through `Ctrl+F` and a clear `Esc` behavior.

**Non-Goals:**

- Adding a Search sidebar destination, section, or count.
- Changing `core/search.py` matching rules, ranking, or result data.
- Adding a command palette, type-to-search, or a new search overlay.
- Changing the vault format, scan, persistence, or background refresh.
- Adding a new index or dependency.
- Redesigning the detail toolbar.

## Decisions

### 1. Search lives in a permanent row beneath the browser header

`WorkspaceView` will build a `browser_search_bar` container between `browser_header` and `browser_divider`. The row contains the existing `search_field` and a clear icon button. The header row keeps the navigation toggle, destination title, refresh, and section actions. `browser_title` gains `expand=True` so it pushes the actions to the end now that the search field no longer expands inside that row.

The header, search row, and divider form a tight top block with zero internal spacing; the existing `SECTION_GAP` remains between that block and `browser_body`. This keeps the search row visually attached to the header instead of floating between the header and the content. The row reuses `HEADER_HEIGHT`; no new dimension token is required unless implementation reveals a different field height. The search field keeps its symbolic prefix icon and uses the full browser width minus the clear action.

**Alternatives considered:**

- **Search as a sidebar destination below Inbox.** Rejected. It turns a global query into a location, implies a scope, adds a navigation step, and conflicts with the HIG sidebar definition and the existing spec's destinations-only rule.
- **On-demand search bar toggled by a header button.** This is the strict default pattern, but Afanes already treats search as a permanent, central entry point. The HIG permits a permanent search entry when search is particularly important, so the dedicated row keeps discoverability and avoids an extra click. The on-demand variant remains a future option if the app later needs the vertical space.
- **Search replacing the header title while active.** This is compact, but it hides the destination context and makes the row less discoverable in normal mode. A permanent row is simpler and keeps the global scope visible.

### 2. Search mode is derived from the existing query, not a new destination

No `WorkspaceSection.SEARCH`, no `BrowserState` field, and no `AppState` field are added. `WorkspaceView` derives `searching = bool(state.browser.query.strip())` in one helper and uses that predicate for the title, the hidden controls, and the result layout. `BrowserState.query` remains the single source of truth, so `Ctrl+F`, the field's `on_change`, destination switches, and background refreshes keep their current behavior.

When `searching` is true:

- `browser_title` shows `BROWSER_SEARCH_TITLE` (**Search results**) instead of the destination label.
- `capture_section` is hidden even when Inbox is the active destination.
- `new_reference_button` and the destination action row are hidden.
- `_browser_controls()` returns `_search_controls()` and does not fall through to the Projects, Log, Review, or References views.
- `_search_controls()` no longer has an `active_section is LOG` branch; it always renders the grouped section headings and note rows. The `LogTimeline` query still supplies matching Log entries, but the Log calendar and date tree are not shown.

When the query is cleared, the same predicate restores the active destination's title, controls, and content. Switching destinations still clears the query through `BrowserState.set_section()`.

**Alternative considered:** Keep the Log calendar and date tree visible during a Log-origin search. Rejected because it makes the search result layout depend on the destination and reintroduces the scope ambiguity the change is removing.

### 3. The sidebar remains unchanged

No Search row is added to `WorkspaceSection`, the section icon map, the sidebar count loop, or the browser title lookup. The navigation tests continue to assert that the sidebar does not contain `browser-search` or the browser list. The new spec requirement states this explicitly so a later change cannot add a Search destination silently.

### 4. Search scope and copy are explicit

The field hint changes from `Title, identity, or text` to `Search all notes…` so the global scope is visible before typing. The search row is the only place the search entry appears. The clear button uses a symbolic close icon, a tooltip, and a key for tests. The button is visible only while the query is non-empty; clearing the query returns the browser to the destination view. The strings use sentence case, matching the current copy wave, and the HIG typographic ellipsis.

### 5. Escape clears search before closing the drawer

`WorkspaceView` gains an async `clear_search()` command that returns whether it cleared a non-empty query. The clear button calls the same path. `app._on_keyboard()` handles `Escape` by awaiting `workspace.clear_search()` first; if it returns `False`, it falls back to `workspace.close_drawer()`. This preserves the existing drawer behavior while giving search a predictable dismissal. Clearing keeps focus in the search field when the field is available; the browser list and results are rebuilt through the existing refresh path.

**Alternative considered:** Bind `Esc` only to the drawer and leave search clearing to the clear button. Rejected because the HIG treats `Esc` as the standard way to leave a transient search context.

### 6. The unreadable-notes rescue section stays separate

The failures area is not a search result group. It remains below the browser list as the existing vertical rescue section so unreadable notes stay reachable; search does not claim to search them. The grouped result list contains only parsed Inbox, Projects, References, Log, and Needs attention matches.

## Risks / Trade-offs

- **The permanent row consumes 48 px in every destination.** → It replaces the cramped in-header field with a full-width row and matches the existing permanent-search decision; the browser can still scroll its content, and the row is absent from the detail region.
- **Hiding destination controls during search may surprise users.** → The title changes to **Search results**, the search row is the focused control, and clearing the query restores the exact destination view and controls.
- **`Esc` now has two jobs.** → Clear search first, close the drawer only when the query is already empty. Tests cover both paths and the ordering.
- **Removing the Log-only search branch changes the old Log search presentation.** → The spec delta makes the new behavior explicit: global results are origin-independent, and the Log calendar/date tree are hidden while a query is active.
- **The existing `ProjectsView` still accepts a query for its standalone refresh path.** → It is not reached while global search is active because `_browser_controls()` returns the search result list first. No core behavior changes.
- **Existing tests locate the search field inside the browser header.** → Update the layout assertion to require it in `browser_search_bar`, not `browser_header`, and add coverage for the title and hidden controls.

## Migration Plan

No data migration. The query is ephemeral view state; no note or settings file changes. The change can ship in one release. Rollback is a code revert; no persisted state depends on the new row or title.

## Open Questions

None that block the design. The on-demand search variant is a deliberate future option, not a dependency of this change.
