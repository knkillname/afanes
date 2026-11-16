# Tasks

## 1. Shortcut discovery

- [x] 1.1 Add the shortcut-sheet, menu-item, group-heading, and key-label copy to the English catalog and Spanish `.po`; classify each new constant; verify `hatch test tests/i18n/test_copy.py` passes.
- [x] 1.2 Add `ui/components/shortcuts.py` with the grouped General, Calendar, and Navigation sheet, a Close action, and Esc dismissal; verify component tests cover grouping, initial focus, and close behavior.
- [x] 1.3 Add Keyboard Shortcuts… to the primary menu and route `Ctrl+?`, including the shifted `/` form, through `AppShell`; verify `tests/ui/test_app.py` and the new shortcut tests cover the menu, both key forms, no destination change, and Esc.
- [x] 1.4 Document the menu entry, `Ctrl+?`, the grouped contents, and the browser interception caveat in `docs/guide/workspace.md`; verify `hatch run docs:build` passes.

## 2. Log calendar keyboard

- [x] 2.1 Add the day-only Log-calendar keyboard adapter for arrows, Page Up/Page Down, Home/End, and Enter; wire it through the workspace and shell; verify tests cover each key and the existing pointer behavior.
- [x] 2.2 Cover month-boundary focus, focus-ring visibility, Tab escape, and Enter parity with a pointer click; verify the calendar and workspace tests pass.
- [x] 2.3 Document the Log calendar keys and the shared day-view contract in `docs/guide/log.md` and `docs/guide/dates.md`; verify `hatch run docs:build` passes.

## 3. Review cards and focus after trash

- [x] 3.1 Replace the pointer-only Review card with the focusable row pattern, including the visible focus ring and keyboard activation; verify Review tests cover focus order, activation, current-item marking, and unchanged review records.
- [x] 3.2 Record the browser’s visible note order before a trash, then focus the next row, previous row, or search field after the move; verify tests cover next, previous, empty, grouped, and active-query cases without changing the destination or query.
- [x] 3.3 Document Review-card keyboard access and the post-trash focus rule in `docs/guide/workspace.md`; verify `hatch run docs:build` passes.

## 4. Accessible names and live regions

- [x] 4.1 Add the clean-sheet accessibility gate in `tests/ui/test_accessibility.py` for buttons, menu actions, icon-only controls, and pointer-only containers; verify it passes the current tree and fails a synthetic unnamed control.
- [x] 4.2 Audit and fix every interactive control the gate reports, adding tooltips, semantics labels, or focusable button wrappers; verify the gate reports zero violations and existing UI tests still pass.
- [x] 4.3 Wrap banners, toasts, and primary inline validation messages in live regions without announcing duplicate copies; verify feedback, banner, and form tests cover the live-region semantics.
- [x] 4.4 Update the accessibility notes and wave 5 status in `docs/develop/interface-standard.md`; verify `hatch run docs:build` passes.

## 5. Large text and rendered layout snapshot

- [x] 5.1 Replace fixed heights on text-bearing headers, fields, calendar cells, and date-picker periods with minimum heights and content growth; verify existing UI tests and new large-text layout tests pass.
- [x] 5.2 Add a test-only 200% theme scale and `scripts/render_layout.py` to launch the cached Flet desktop client with a temporary fixture vault, record keyed control geometry at 100% and 200%, and close the window; verify the command runs and writes a temporary JSON report.
- [x] 5.3 Add the JSON snapshot comparator and Linux snapshot, failing on missing views, collapsed regions, non-growing text controls, and geometry outside tolerance; verify pass, non-growing, missing-view, and tolerance cases, with no tracked screenshots.
- [x] 5.4 Add the `hatch run render:check` and `hatch run render:update` commands and document the display prerequisite and snapshot review rule; verify both commands are documented and `hatch run render:check` passes.
- [ ] 5.5 Run the real GNOME Large Text pass at 1024x600, the 1100 px breakpoint, light and dark, across every primary view; record the observed result in `RELEASE.md` and do not mark this task complete without evidence.
- [ ] 5.6 Update the wave 5 evidence and HIG row in `RELEASE.md` and the guide references to the automated layout check; verify `hatch run docs:build` passes.

## 6. Integration checks

- [ ] 6.1 Run `hatch check`; verify lint, formatting, and strict types pass.
- [ ] 6.2 Run `hatch test --cover`; verify the suite passes at 85% coverage or higher.
- [ ] 6.3 Run `hatch run render:check`; verify the Linux layout snapshot passes.
- [ ] 6.4 Run `openspec validate --all --strict` and `openspec doctor`; verify both pass.
- [ ] 6.5 Run the vocabulary greps, `git diff --check`, and the tracked-`.mo` check; verify no prohibited matches, a clean diff, and no tracked compiled catalogs.
- [ ] 6.6 Run `hatch run docs:build`; verify the documentation build passes.

## Workflow follow-up

- Archive the change after review; the archive syncs the `interface-theme`, `vault-browsing`, and `note-log` deltas.
- Run the post-archive release workflow in `AGENTS.md` 5.3. Assess whether wave 5 completes a coherent milestone; update `CHANGELOG.md`, `README.md`, and docs if the release step calls for it.
- Do not tag, push, or publish unless asked.
