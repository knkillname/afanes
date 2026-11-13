# Design

## Context

See `proposal.md` — Why for the motivation and the shell's HIG references.

The current `WorkspaceView.root` is a column with a capture row, a banner column, a row holding the
sidebar and `main_host`, and a status bar. The sidebar container holds the Review entry, the section
entries, the search field, `browser_list`, and the failures column. `_browser_controls()` already
returns the active section's body (a flat list, `ProjectsView`, the Log calendar and tree, or a
failure list), and `_refresh_main()` already selects the page pane, the Processing Wizard, or the
Review view for the detail. The shell therefore has the content it needs; it keeps three
information layers in one 260 px column.

`BrowserState` owns the active destination, the query, and the Log state. `BrowserListing.filtered()`
already filters every group; the view narrows the result to the active section. `theme.py` defines
`LIST_WIDTH = 360` and `PAGE_MIN_WIDTH = 420`, neither of which is used yet.

Flet exposes `page.width` and `page.on_resize`, so the shell can choose a layout from the viewport.
Flet desktop windows keep native decorations; the application cannot draw into the title bar.

## Goals / Non-Goals

**Goals:**

- A three-region shell: navigation, browser, and detail, with one owner and one subject each.
- A global search surface, a toolbar that reflects the active view, and the primary menu in the
  HIG-prescribed position above the navigation list.
- An adaptive ladder that keeps the browser useful at 1024x600 and degrades to a browse-to-detail
  stack in a narrow browser presentation.
- Bounded column widths and a maximum reading width.
- One additional bounded difference: the native title bar.

**Non-Goals:**

- The rest of the HIG waves: the remaining control-hierarchy debt outside the page toolbar, writing
  style, undo/toasts, the full keyboard map, placeholder pages, and the application icon.
- Changing core search matching, the vault format, the CLI, or any dependency.
- Re-rendering note bodies without their leading heading. The detail toolbar shows the page title
  and the reading view keeps its current Markdown, including the H1; removing the duplicate is a
  content-view change for a later wave.

## Decisions

### 1. Three regions with one owner each

- **Navigation** (`WorkspaceView.navigation`): destinations, counts, the Review entry, the vault
  identity, and the primary menu. No list, no search.
- **Browser** (`WorkspaceView.browser_region`): the active destination's header (title, search, and
  section actions) and body. The body is the existing `_browser_controls()` output: the flat list,
  `ProjectsView`, the Log controls, or the failures list. The Inbox body gains the capture composer.
- **Detail** (`WorkspaceView.detail_region`): the in-window toolbar and `main_host`. `main_host`
  keeps the page pane, Processing Wizard, or Review view.

`PageView` splits its current header from its card body: `toolbar()` returns the Back, title, one
primary action, and secondary menu controls, and `body()` returns the banners, dialogs, and mode
host. The workspace places both. The page's path, metadata, and status move out of the toolbar into
the body or a banner so the toolbar stays a header bar, not a document header.

*Alternative rejected:* keep the page header inside the card. It avoids the split but leaves
several suggested actions in one row, does not align the three columns' headers, and does not
relieve the 1024 px width pressure.

*Alternative rejected:* the two-pane browse/read stack as the desktop layout. It is a valid HIG
browsing pattern at narrow widths, but as the only layout it loses simultaneous browsing and
reading and changes the workspace contract. It remains the narrow presentation in the ladder.

### 2. Adaptive ladder

`_Shell` reads the viewport width — the window width on desktop and the page width in a browser
presentation — after the workspace is built and on every `page.on_resize`, then calls
`workspace.resize(width)`. The workspace stores the breakpoint and re-renders the shell without
changing the page, destination, or query.

| Viewport | Arrangement |
| --- | --- |
| `>= 1100` | navigation, browser, and detail side by side |
| `1024-1099` | browser and detail; navigation behind a toggle |
| `< 1024` (web) | one region at a time; browser is the root, Back returns from the detail |

The navigation toggle opens a transient drawer. Selecting a destination or pressing Esc closes it.
The desktop minimum becomes 1024x600, so the medium layout is used at exactly 1024. The three-column
layout starts at the default 1100 px window.

*Alternative rejected:* keep three fixed columns down to 1024. The HIG warns that small panes are
hard to make adaptive, and the detail would fall below its minimum content width.

*Alternative rejected:* collapse the browser first at medium widths. The list is the more valuable
pane while reading; the navigation is a destination switcher that can live behind a toggle.

### 3. Toolbar and action hierarchy

The detail toolbar holds Back, the page title, one primary action, a secondary menu, and the progress
ring. The title uses the `title-3` role on one line rather than the reading view's `title-1`, so it
fits the shared header height; the reading view keeps its own heading hierarchy. The primary action
follows the view: Process for an unclarified capture, Edit for a readable note, Save in edit mode.
Rename, Move to Trash, and the other page commands move to the secondary menu. The trash
confirmation stays a dialog until the feedback wave replaces it with undo.

The header bar is one of the HIG's icon-and-label exceptions, but the workspace prefers icon-only
secondary controls to keep the conformance ledger flat. The single primary action may use the
suggested style. The gate's suggested/destructive count for `PageView` must shrink; the
icon-and-label count must not grow.

The browser header is a separate header aligned with the detail toolbar: destination title, the
permanent global search entry, and the destination's actions (New Reference; Log's Entries,
Everything, and Today's Entry).

### 4. Global search

The search entry stays permanently visible at the top of the browser region. It is the only query
field. When the query is empty the browser shows the active destination; when it is non-empty the
browser shows every matching group with section headings. The active destination does not filter
the results. `BrowserListing.filtered()` already filters every group, so no core change is needed.

Switching destinations clears the query, so navigation exits search. The navigation counts remain
totals: add an unfiltered `BrowserState.counts()` derived from `Browser(snapshot).groups()` and an
unfiltered Log timeline, and use it for the navigation. The result groups show their own match
counts. The Log calendar and tree keep using the query. The no-match state names the query.

Ctrl+F focuses the search entry. Ctrl+N is the shell's other shortcut; the full keyboard map
belongs to the keyboard wave.

*Alternative rejected:* a header-bar search toggle that slides a search bar under the toolbar. It is
the HIG's typical pattern, but Afanes' search is central and the HIG explicitly allows a permanent
entry when search is particularly important. The permanent entry also avoids a second hidden mode.

*Alternative rejected:* keep section-scoped search. It contradicts the HIG's global-search guidance
and is the direct cause of the "cramped sidebar" complaint.

### 5. Capture

The composer moves to the top of the Inbox browser body, directly above the Inbox list. Its Capture
button remains the single suggested action in the workspace shell; New Reference, Today's Entry,
and the other browser actions use regular buttons so the shell never carries two suggested actions.
The page detail keeps its own single suggested action. A New Capture toolbar action with Ctrl+N
switches to Inbox and focuses the field from any other destination, and that action is regular
rather than suggested.

*Alternative rejected:* a header-only capture dialog. It is the standard "new item" shape, but it
adds a step to the app's most frequent action and discards a well-tested composer.

### 6. Primary menu and vault identity

The navigation header shows the vault name and a primary menu button (tooltip and accessible name
"Main Menu"). The menu sits above the navigation list, as the HIG requires when a window has a
sidebar. It offers Change Vault…, Create Vault…, Close Vault, and About Afanes. The existing
commands are reused. About opens a small dialog with the application name, version from
`afanes.__about__`, and license; the icon arrives with the identity wave.

The status bar is removed. The vault name keeps the full path in a tooltip, which satisfies the
"full path available" scenario without a status bar.

*Alternative rejected:* keep the status bar and move only the menu. The HIG has no status-bar
pattern, and the vault path is better placed with the vault identity.

### 7. Review queue

While Review is active, the browser shows the session's snapshot queue from
`review.review_session.items`, in order, with the current item marked by the neutral selected-row
token. Rows are read-only: review actions stay in the detail card. This gives the Review
destination a browser body without adding queue navigation or changing review state.

*Alternative rejected:* make queue rows jump to an item. That is a new review behavior and needs
its own spec and state command; it is better as a later guided-review change.

### 8. Surfaces and chrome

Navigation uses the sidebar surface, the browser uses the window surface, and the detail uses the
note-view surface. The four reference roles stay unchanged; the browser does not add a fifth role.
The navigation is a bordered panel with the surface radius, structural in the wide layout and
elevated with a shadow as a drawer. The browser is flush, and the detail keeps its card border and
radius. The three headers share one height token.

### 9. Widths and content bounds

Add tokens for the navigation width, browser minimum and maximum, detail minimum content width, and
maximum reading width. Proposed values:

```text
NAVIGATION_WIDTH   240
BROWSER_MIN_WIDTH  320
BROWSER_MAX_WIDTH  360
PAGE_MIN_WIDTH     420
CONTENT_MAX_WIDTH  720
SHELL_WIDE_MIN     1100
SHELL_MEDIUM_MIN   1024
HEADER_HEIGHT       48
```

The detail card may span the detail region, but its prose and forms stay within `CONTENT_MAX_WIDTH`
and centre on very wide windows. The existing unused `LIST_WIDTH` is replaced by the browser
tokens.

### 10. Native title bar

Flet desktop windows use native decorations and expose no API to host application controls in the
title bar. The workspace therefore provides an in-window toolbar aligned with the two headers. This
joins the bounded differences in `interface-theme` as the fifth toolkit limit.

## Risks / Trade-offs

- [The 1024 medium layout squeezes the detail] → browser maximum 360 and detail minimum 420; test at
  1024x600; collapse the navigation first.
- [Splitting `PageView` breaks page state and tests] → keep the existing public attributes, move
  only the header composition, and verify edit, save, rename, trash, and conflict flows.
- [Global results overwhelm the browser] → section headings, per-group counts, and the active page
  remain visible; no-match state; destination switch clears the query.
- [Navigation counts become misleading during search] → keep totals from an unfiltered listing and
  show match counts in the result groups.
- [The read-only review queue looks interactive] → plain rows with no hover or click affordance; mark
  only the current item.
- [Resize events lose state] → the workspace stores the breakpoint and re-renders only the shell;
  test with direct `resize()` calls across each boundary.
- [New toolbar buttons grow the conformance ledger] → prefer icon-only secondary controls; shrink
  the page's suggested action count; never add a baseline entry.
- [The toolbar title duplicates the body H1] → keep the reading view unchanged and record the
  duplicate as a content-view follow-up, not part of this change.
- [Removing the status bar hides the vault path] → the vault name keeps a tooltip with the full
  path; the About dialog names the application.

## Migration Plan

1. Add the shell tokens, surfaces, and minimum window; update the theme tests.
2. Split `PageView` into toolbar and body; move the page command set into one primary action and a
   secondary menu; update the page tests.
3. Recompose `WorkspaceView`: navigation, browser header and body, detail toolbar, aligned headers,
   no status bar.
4. Add the primary menu, About dialog, vault identity, and the capture composer placement.
5. Make search global, clear it on destination switch, and switch navigation counts to totals.
6. Add the Review queue, the adaptive ladder, the drawer, and the resize wiring.
7. Rebuild the conformance baseline down to the new counts, then run the full gates and the visual
   review at 1024x600, 1100x760, and a wide window in both modes.

No data migration is required. Reverting the change restores the two-pane shell; the vault and
settings formats are untouched.

## Open Questions

None that change the requirements, the approach, or the task breakdown. The duplicate leading
heading in the reading view is recorded as a deferred content-view decision, not a shell question.
