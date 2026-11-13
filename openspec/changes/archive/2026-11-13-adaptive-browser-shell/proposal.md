# Proposal

## Why

The workspace is still a two-pane shell with one 260 px sidebar carrying navigation, the search
field, the section list, and the Log calendar. The GNOME HIG defines a sidebar as a list of
locations and treats lists as content views, so the current arrangement both cramps the browser
and forces a two-level navigation structure through one column. Search is also scoped to the active
section, while the HIG expects results from all views.

The appearance standard is already strict. This change applies the same strictness to structure,
search, and adaptivity before the remaining HIG waves.

## What Changes

- **BREAKING** (UI): re-compose the workspace into a navigation sidebar, a browser column, and a
  detail pane. The sidebar holds only destinations, counts, vault identity, and the primary menu.
  The search entry, section actions, list or calendar, and unreadable-note list move into the
  browser column.
- Add aligned in-window headers for the navigation, browser, and detail regions: the vault identity
  and primary menu, the destination title and global search, and the page title, Back, one suggested
  action, and a secondary menu. The OS title bar stays native; no controls are drawn into it.
- Make search global. A query filters every section and the browser column shows section-grouped
  results; the Log calendar and tree remain filtered by the same query. Ctrl+F focuses the search
  entry.
- Add the primary menu above the navigation list with Change Vault…, Create Vault…, Close Vault, and
  About Afanes. Remove the status bar; the vault identity moves to the navigation region.
- Move the capture composer to the top of the Inbox browser column. A New Capture action (Ctrl+N)
  switches to Inbox and focuses the composer from any other destination.
- Show the guided-review snapshot queue in the browser column while Review is active as selectable
  cards; selecting one makes it current, and the review actions stay in the detail pane.
- Replace the fixed width with three columns and a breakpoint ladder: navigation + browser + detail
  at 1100 px and above; browser + detail with the navigation behind a toggle at 1024-1099; a
  browse-to-detail stack below 1024 (web). Raise the minimum window to 1024x600, the HIG desktop
  floor.
- Give the list column a minimum and maximum width and give the detail pane a maximum content
  width for large windows.
- Declare one additional toolkit limit: Flet desktop windows use native decorations, so the
  application cannot draw controls into the title bar. The in-window toolbar is the HIG header
  bar's structural equivalent.
- Keep the current palettes, type scale, icon treatment, and selection rules. Move the surfaces
  onto the new columns: sidebar chrome, window-level browser, elevated note view.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `vault-browsing`: the workspace shell gains a navigation region, a browser column, and a detail
  pane; the browser stays visible at wide sizes and becomes a browse-to-detail stack at narrow
  sizes; search returns section-grouped results from the whole vault; the capture composer and
  section actions move into the browser column; the primary menu and vault identity replace the
  status bar; the Review destination shows the snapshot queue.
- `interface-theme`: the workspace gains navigation, browser, and detail width tokens with minimum
  and maximum values; the surface assignment names the browser column; the minimum window becomes
  1024x600; the bounded-differences requirement gains the native-title-bar limit. The existing
  palette, type, icon, and selection requirements are unchanged.

## Impact

- UI: `src/afanes/ui/views/workspace.py` (shell composition, columns, toolbar, menu, breakpoints),
  `src/afanes/ui/views/projects.py` (browser-column layout), `src/afanes/ui/views/review.py`
  (queue rendering), `src/afanes/ui/views/page.py` (header actions), `src/afanes/ui/app.py` (window
  minimum), `src/afanes/ui/theme.py` (width tokens, surfaces, toolbar metrics),
  `src/afanes/ui/strings.py` (new labels), `src/afanes/ui/components/calendar.py`,
  `log_tree.py` (column width), a new About dialog component, and
  `src/afanes/ui/state/browser.py` (global results presentation).
- Tests: `tests/ui/test_workspace_view.py`, `test_projects_view.py`, `test_review_view.py`,
  `test_page_view.py`, `test_app.py`, `test_theme.py`, `test_conformance.py`, `test_state.py`.
- Docs: `docs/develop/interface-standard.md`, `docs/guide/workspace.md`, `docs/guide/log.md`,
  `docs/guide/inbox.md`, `docs/guide/review.md`, and the four screenshots. `README.md` only if it
  describes the workspace.
- No runtime dependency, vault format, CLI, or data-model change. The search core already evaluates
  every group; the change is presentation and state scope.
- Cross-platform parity: the breakpoint ladder covers desktop and web; the native-title-bar limit
  applies to every platform.
