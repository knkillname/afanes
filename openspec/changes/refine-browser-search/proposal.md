# Proposal

## Why

The browser header currently shares one row between the active destination title and the permanent global search field. That makes a vault-wide search look like a filter for Inbox, Projects, or whichever section is selected. The 320–360 px browser column leaves the field cramped beside the title, refresh action, and section actions. The problem is worse while a query is active: the title still names the destination, the Inbox composer or References action can remain visible, and the Log calendar can leak into the result view even though the matches span every destination.

The GNOME HIG keeps navigation locations and content search separate. Sidebars list locations; search is a global filter in the content view, normally presented as a search bar beneath the header. Afanes should keep the second column as the home of search, but give the search entry its own full-width row and make the global search mode explicit. It should not add a Search destination to the sidebar.

## What Changes

- Move the global search field out of the browser header and into a permanent, full-width search row directly beneath the browser header. The row uses the browser width and a clear action; the header keeps only the destination title and its actions.
- While the query is non-empty, the browser title becomes **Search results**. The browser replaces destination-specific content with one global result list grouped by destination. The Inbox composer, References New Reference action, Log calendar/date tree, Review queue, and other destination-specific controls are hidden during the search.
- Keep the sidebar unchanged: Review, Inbox, Projects, References, Log, and Needs attention remain destinations with counts. Search is not added as a sidebar row or a `WorkspaceSection`.
- Make the search scope explicit in the field hint and keep search global. `Ctrl+F` focuses the permanent field. `Esc` clears a non-empty query before closing the navigation drawer; the clear action does the same.
- Preserve the current query semantics: search matches display title, identity, prose body, step text, and role names; matching ignores case, Unicode form, and repeated whitespace; switching destinations clears the query; destination counts remain totals.
- Update the workspace documentation and interface standard to describe the dedicated search row, the search-results title, and the hidden destination-specific controls.
- Add regression coverage for the row placement, title change, hidden controls, global result grouping, clear action, `Ctrl+F`, and `Esc`.

This is a visual and interaction change only. It does not change the vault format, scan, search matching rules, note model, or persistence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `vault-browsing`: The browser shell requirements change so the global search entry has its own row beneath the browser header, the browser title reflects the search mode, and destination-specific browser content is replaced while a query is active. The sidebar remains destinations-only and search remains global.

## Impact

- **UI**: `src/afanes/ui/views/workspace.py` for the browser header, search row, title, hidden controls, and result layout; `src/afanes/ui/strings.py` for the search title, hint, and clear action; `src/afanes/ui/app.py` for `Esc` routing; `src/afanes/ui/theme.py` only if the search row needs a named height token.
- **Tests**: `tests/ui/test_workspace_view.py` and `tests/ui/test_app.py`.
- **Documentation**: `docs/guide/workspace.md` and `docs/develop/interface-standard.md`.
- **Specs**: delta for `vault-browsing`; no new capability.
- **Out of scope**: adding a Search sidebar destination, changing search matching in `core/search.py`, changing the vault format, and adding a new index or dependency.
