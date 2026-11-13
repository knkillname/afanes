# Tasks

## 1. Shell tokens and window bounds

- [x] 1.1 Add the shell tokens to `src/afanes/ui/theme.py`: `NAVIGATION_WIDTH`, `BROWSER_MIN_WIDTH`,
  `BROWSER_MAX_WIDTH`, `PAGE_MIN_WIDTH` (keep the existing value), `CONTENT_MAX_WIDTH`,
  `SHELL_WIDE_MIN`, `SHELL_MEDIUM_MIN`, and `HEADER_HEIGHT`. Set `WINDOW_MIN_WIDTH = 1024`, remove
  the unused `LIST_WIDTH`, and keep `WINDOW_MIN_HEIGHT = 600`. Verify with
  `hatch test tests/ui/test_theme.py` that every token exists with the designed value, the old name
  is gone, and the minimum window is 1024x600.
- [x] 1.2 Add theme tests for the width relationships: browser minimum is below its maximum, detail
  minimum is below the content maximum, the wide breakpoint is above the medium breakpoint, and the
  header height is positive. Verify `hatch test tests/ui/test_theme.py` passes.
- [x] 1.3 Update the token and minimum-window sections of `docs/develop/interface-standard.md` with
  the new column widths, breakpoints, and 1024x600 minimum. Verify `hatch run docs:build` succeeds.

## 2. Page toolbar and action hierarchy

- [x] 2.1 Split `PageView` into `toolbar()` and `body()`: the toolbar keeps Back, the page title, one
  primary action, and a secondary menu; the body keeps the banners, dialogs, and mode host. Keep
  `build()` returning a complete page for callers that still need it. Verify
  `hatch test tests/ui/test_page_view.py` passes.
- [x] 2.2 Move the page commands into the new hierarchy: Process is primary for an unclarified
  capture, Edit is primary for a readable note, Save is primary in edit mode, and Rename, Move to
  Trash, and the remaining commands move to the secondary menu. Move the path, metadata, and status
  out of the toolbar. Verify the process, edit, save, rename, trash, conflict, and rescue tests pass
  and only one suggested action remains.
- [x] 2.3 Update the `PageView` suggested/destructive and icon-and-label baseline entries in
  `tests/ui/test_conformance.py` to the new counts and delete any stale entry. Verify
  `hatch test tests/ui/test_conformance.py` passes in both directions.
- [x] 2.4 Update `docs/guide/pages-and-editing.md` if it describes the old page action row; state
  that the page title and primary action live in the detail toolbar and the remaining commands live
  in the secondary menu. Verify `hatch run docs:build` succeeds.

## 3. Workspace shell

- [x] 3.1 Recompose `WorkspaceView` into `navigation`, `browser_region`, and `detail_region`, remove
  the status bar and the top capture row, and keep `root`/`build()` as the shell entry point. Verify
  `hatch test tests/ui/test_workspace_view.py` passes after updating its structural assertions.
- [x] 3.2 Build the navigation region: destinations, counts, Review entry, vault identity, and the
  primary menu button, using the neutral selected row and monochrome icons. Verify a workspace test
  asserts the destinations are present, the browser list and search are absent, and the selected
  entry uses the neutral token.
- [x] 3.3 Build the browser region: a header with the destination title, the permanent search entry,
  and the destination actions, plus the existing body for the flat list, `ProjectsView`, the Log
  controls, and the failures list. Move the Inbox composer above the Inbox list. Verify a workspace
  test asserts the composer appears only in Inbox and the section bodies still render.
- [x] 3.4 Build the detail region: an aligned toolbar host, the page view, the Processing Wizard, and
  the Review view. Verify a workspace test asserts the page, processing, and review detail controls
  all render in the detail region.
- [x] 3.5 Assign the surfaces: navigation uses the sidebar token, the browser uses the window token,
  the detail uses the note-view token, and the navigation is flush chrome rather than a rounded
  card. Verify `hatch test tests/ui/test_theme.py tests/ui/test_workspace_view.py` passes for the
  three surfaces and the absence of the old sidebar card.
- [x] 3.6 Update the `WorkspaceView` numeric-layout, suggested/destructive, icon-and-label, and dense
  row baseline entries in `tests/ui/test_conformance.py` to the new counts. Verify
  `hatch test tests/ui/test_conformance.py` passes with no new violation and no stale entry.
- [x] 3.7 Rewrite the layout and differences sections of `docs/develop/interface-standard.md`: the
  three regions, the surface assignment, the native-title-bar limit as the fifth bounded
  difference, and the toolbar rules. Verify `hatch run docs:build` succeeds.
- [x] 3.8 Update `docs/guide/workspace.md` for the three-region workspace, the navigation and
  browser split, the detail toolbar, and the surface story. Verify `hatch run docs:build` succeeds.
- [x] 3.9 Update `AGENTS.md` 4.6 to name the three-region shell, global search, the primary menu
  position, the 1024x600 minimum, and the fifth Flet limit. Verify the references are present and
  the documented commands still exist.

## 4. Search, menu, capture, and review queue

- [x] 4.1 Make the browser search global: when the query is non-empty, render every matching group
  with section headings and per-group counts; when it is empty, render the active destination.
  Verify a workspace/state test covers matches from Inbox, Projects, References, and Log, and that
  the no-match state names the query.
- [x] 4.2 Clear the query when the destination changes (`BrowserState.set_section`) and switch the
  navigation counts to unfiltered totals (`BrowserState.counts()` plus an unfiltered Log count).
  Verify tests cover a destination switch leaving search, totals while a query is active, and the
  Log calendar/tree still using the query.
- [x] 4.3 Add the primary menu above the navigation list with Change Vault…, Create Vault…, Close
  Vault, and About Afanes; add the About dialog with the application name, version, and license; and
  move the vault name and full-path tooltip into the navigation header. Verify app and workspace
  tests cover each menu command, the About dialog, and the absence of the status bar.
- [x] 4.4 Add the New Capture toolbar action and Ctrl+N, and add Ctrl+F to focus the search entry.
  Make Capture the only suggested action in the workspace shell; make New Reference, Today's Entry,
  and the other browser actions regular buttons. Verify a workspace test covers switching to Inbox
  and focusing the composer from another destination, and that the composer's Capture button is the
  only suggested action in the workspace.
- [x] 4.5 Show the Review session's snapshot queue in the browser as selectable cards, in order,
  with the current item marked; selecting a card changes only the current item. Verify review and
  workspace tests cover the order, the current mark, card selection, a completed session, and a note
  created during the session not joining the queue.
- [x] 4.6 Update the `WorkspaceView` and `AppShell` baseline entries in
  `tests/ui/test_conformance.py` for the new menu, capture, and review controls. Verify
  `hatch test tests/ui/test_conformance.py` passes.
- [x] 4.7 Update `docs/guide/workspace.md` for global search, the menu, and capture; update
  `docs/guide/inbox.md` for the composer placement; update `docs/guide/review.md` for the browser
  queue; update `docs/guide/log.md` if the Log controls moved. Verify `hatch run docs:build`
  succeeds.

## 5. Adaptive layout

- [x] 5.1 Add `WorkspaceView.resize(width)` and raise it from `_Shell` after the workspace is built
  and from `page.on_resize`, using the desktop window width or the web page width. Verify an app test
  covers the initial call and a resize event, and a workspace test covers the stored breakpoint.
- [x] 5.2 Implement the three arrangements: three regions at 1100 and above; browser and detail with
  the navigation behind a transient drawer at 1024-1099; one region at a time below 1024 with the
  browser as the root and Back returning from the detail. Verify workspace tests cover each
  breakpoint, the drawer's selection and Esc close, and state preservation across a resize.
- [x] 5.3 Verify the desktop minimum window is 1024x600 and the shell shows no clipped navigation,
  browser, header, or detail control at 1024x600 and 1100x760 in both modes. Record the values in
  the change notes if any token needs adjustment.
- [x] 5.4 Update the adaptive and breakpoint sections of `docs/develop/interface-standard.md` and
  `docs/guide/workspace.md`, and regenerate the four screenshots for the new shell. Verify
  `hatch run docs:build` succeeds and each image shows the three regions.

## 6. Verification

- [x] 6.1 Rebuild the conformance baseline one final time and confirm no stale entry remains, then
  run `hatch test tests/ui/test_conformance.py`. Verify the gate passes in both directions.
- [x] 6.2 Run `hatch check` and `hatch test --cover`; confirm the suite passes at 85% coverage or
  higher with the parser, link, and vault modules at 90%. Verify both commands exit clean.
- [x] 6.3 Run `openspec validate --all --strict`, `openspec doctor`, and the vocabulary checks from
  `AGENTS.md` 6.1. Verify all exit clean with no output from the grep commands.
- [x] 6.4 Review the built interface at 1024x600, 1100x760, and a wide desktop size in light and
  dark mode, plus a narrow browser presentation, and confirm every shell spec scenario is
  observable. Record any deviation in the change notes.
- [x] 6.5 Check `README.md` for stale workspace statements and update it only if it describes the
  shell, search placement, or the status bar. Verify `hatch run docs:build` still succeeds.

## Workflow follow-up

- Archive the change after the maintainer reviews the artifacts and the implementation gates pass.
- Run the post-archive release workflow from `AGENTS.md` 5.3; bump only if the archive completes a
  coherent milestone.
- Move the next HIG wave (control hierarchy, writing style, feedback, keyboard and accessibility,
  identity) to its own change.
