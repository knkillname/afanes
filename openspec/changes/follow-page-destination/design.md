# Design

## Context

See `proposal.md` for motivation and `specs/vault-browsing/spec.md` for the behavior contract.

`BrowserState` owns `active_section`, the query, and the Log lens. `PageNavigator.open_page()` owns
the page load and the bounded history, but never updates the browser. The Review flow already selects
a destination after opening a project or reminder, with its own note-type map in `review.py`. That
local map is the only existing coupling between an open page and the navigation destination.

The browser groups notes by path first (`inbox/`) and then by type. The Log and Trash destinations are
not core browser groups: Log comes from the date timeline, and Trash comes from the managed catalog.
The page history stores paths only.

## Goals / Non-Goals

**Goals:**

- One destination rule for every page that has a browser group.
- Search result selection leaves search and shows the result's destination.
- Back restores the destination of the page it returns to.
- Manual destination selection keeps the open page.
- Remove the duplicate Review destination map.

**Non-Goals:**

- Changing the browser groups, the scan, the vault format, or the CLI.
- Closing the open page when the reader selects another destination.
- Expanding a collapsed project group or moving the Log calendar to the opened entry's date. The
  destination follows; the destination's internal expansion and calendar state do not.
- Giving an unsaved draft a browser destination. A draft is not in the scan; it keeps the current
  destination until it is written and becomes a note. The missing-role-name flow is included because
  it writes and opens a real note.
- New dependencies, network access, or persisted UI state.

## Decisions

### 1. `BrowserState` owns the note-to-destination mapping

Add a synchronous lookup to `BrowserState` that takes a page path and returns its
`WorkspaceSection`, or `None` when the note is not in the active snapshot. The lookup uses the
snapshot's note lookup rather than comparing raw filesystem paths. It follows the browser's grouping
precedence:

| Note | Destination |
| --- | --- |
| Path under `inbox/` | Inbox |
| `type: project` outside `inbox/` | Projects |
| `type: reference` outside `inbox/` | References |
| `type: log` outside `inbox/` | Log |
| `type: note` outside `inbox/` | Needs attention |
| Managed trashed entry | Trash, selected by the Trash flow |
| Unparseable file | None |

The path check runs first, matching `Browser.groups()`: a note under `inbox/` selects Inbox even
when its type is project, reference, or log. Normal vaults keep each type in its conventional
folder, so the later rows cover the ordinary cases.

The mapping stays in UI state because Log and Trash are workspace destinations, not core
`BrowserSection` values. Putting it in `core/search.py` would make core learn presentation
destinations. A separate mapper object would add a collaborator without owning new data.

### 2. Page navigation shares one selection path with explicit destination selection

`BrowserState` already has the asynchronous `set_section()` command used by the sidebar. Add a
synchronous page-following method that sets the mapped section and clears the query, without taking
the command lock. `PageNavigator.open_page()` calls it after a successful `pages.load()` while the
lock is already held. `set_section()` keeps its lock and its Trash maintenance, and uses the same
assignment step as the page-following method.

This avoids an async lock re-entry in `open_page()` and keeps one definition of “select a
destination and clear search.” A private assignment helper may hold the shared two-line mutation;
both public commands remain directly testable.

`open_page()` is the shared entry for browser rows, search results, body links, role names,
connection entries, ambiguous candidates, and review pages, so every one follows the rule. Manual
sidebar selection calls `set_section()` instead and therefore keeps the page.

### 3. Back follows the destination of the restored page

`PageNavigator.back()` loads history entries directly, so it calls the same page-following method
after each successful load. If a history entry is missing, it is skipped without changing the
destination. When the history is exhausted, the page pane is cleared and the current destination is
left in place.

The destination is derived from the restored page, not stored in every history entry. This keeps the
existing path-only history and its limit. Consequence: a manually chosen destination is not replayed
by Back; the page's own destination wins. That matches the rule that navigation follows the content.

### 4. Search results leave search

A non-empty query currently keeps the origin destination. With the new rule, selecting a result calls
`open_page()`, which maps the result note and clears the query. The browser then shows the result's
normal destination with the result selected. Entering a query still does not change the destination;
only selecting a result does.

Alternative rejected: keep the result list while changing the destination. It would show search
results under a sidebar entry that no longer owns the browser content, and the reader chose the
simpler “leave search” behavior.

### 5. Review and creation reuse the shared behavior

`ReviewState.open_project()` and `open_reminder()` keep calling `open_page()`, then drop their local
`set_section()` calls and `_reminder_section()` map. The page-following method produces the same
Projects and note-type destinations and keeps the existing review tests meaningful.

`create_role_reference()` and `create_reference()` call the page-following method after their
successful `pages.load()`. The missing-role-name flow therefore leaves the project browser and shows
References with the new note selected.

`open_trash()` keeps its current workspace flow: the Trash selection already clears the query and
runs retention before the read-only page opens.

### 6. Unreadable notes keep the current destination

The scan stores unparseable files as failures, not browser notes. The mapping returns `None`, so raw
rescue mode opens without changing the sidebar or browser. This preserves the existing failure list
and avoids inventing an Unreadable destination.

## Risks / Trade-offs

- **The project list disappears when an owner reference opens.** Back returns to the project and
  Projects, and manual destination selection still lets the reader browse Projects while the
  reference stays open. Accepted for a sidebar that matches the content.
- **Search results disappear on selection.** The reader chose this over keeping the result list. The
  query can be re-entered; Back returns through pages without restoring the query.
- **Manual destination selection can still leave a page from another destination open.** This is the
  deliberate escape hatch: the sidebar then describes the browser, not the page. The browser shows no
  selected row when the page is not in that destination.
- **A log entry or a closed project may not be visible inside its destination after the switch.**
  The destination follows, but the Log calendar and the project group expansion do not. This is
  explicitly out of scope; a later change can add in-destination reveal.
- **A search result row is removed while it may hold keyboard focus.** Verify the existing focus
  behavior after the change; if focus is lost, restore it to the page or the destination's first
  control without changing the destination.
- **Path lookup can miss a page after an external move.** A missing snapshot note leaves the
  destination unchanged; the existing conflict and refresh paths still report the missing page.
