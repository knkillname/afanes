# Tasks

## 1. Palette and tokens

- [x] 1.1 Add the libadwaita 1.8.0 reference tokens to `src/afanes/ui/theme.py`: window, sidebar, view, header-bar, secondary-container, body and muted text, accent fill and text, on-accent, destructive (Red 3 light / Red 4 dark), border, notice, and status roles. Verify with a token test that pins the reference version, every required role resolves, and the light and dark tables are distinct.
- [x] 1.2 Replace `CARD_RADIUS` with `SURFACE_RADIUS = 12` (`$card_radius`) and `CONTROL_RADIUS = 9` (`$button_radius`); move spacing to `ITEM_GAP = 12`, `SECTION_GAP = 18`, `PAGE_PADDING = 24`. Verify with a token test that the new names exist, the values match the reference, and the old name is gone.
- [x] 1.3 Build `LIGHT_THEME` and `DARK_THEME` as separate `ft.Theme` objects with explicit `ft.ColorScheme` values and `surfaces=ft.ThemeSurfaces.NEUTRAL`; remove the shared `THEME`. Verify with a test that both expose a `color_scheme`, that they are different objects, and that `THEME` no longer exists.
- [x] 1.4 Assign `page.theme = LIGHT_THEME` and `page.dark_theme = DARK_THEME` in `src/afanes/ui/app.py`, and keep the page background on `PAGE_SURFACE_COLOR`. Verify in `tests/ui/test_app.py` that the two assignments are distinct and the background token is used.
- [x] 1.5 Update the contrast assertions: body and muted text meet 4.5:1 on the window, sidebar, view, and container in both modes; accent text meets 4.5:1 on the view; accent fill, icons, control boundaries, and destructive fill meet 3:1; record the suggested-fill label at 3.77:1 as inherited from the reference. Verify the computed ratios pass for the reference tokens.
- [x] 1.6 Update the existing assertions in `tests/ui/test_theme.py` that pin the retired `ACTION_COLOR`, `CARD_RADIUS`, and old selection values. Verify `hatch test tests/ui/test_theme.py` passes.
- [x] 1.7 Add the GNOME standard text roles (`title-1` through `title-4`, `heading`, `body`, `caption`, `caption-heading`) as relative percentages of `BASE_FONT_SIZE = 15`, expose them through a `TEXT_ROLES` value object, map them to the Flet `TextTheme` slots, and attach the theme to both palettes. Verify with a test that every role resolves and each size and weight matches the reference scale.
- [x] 1.8 Replace the Material `theme_style=ft.TextThemeStyle.<slot>` call sites with the GNOME standard roles from `TEXT_ROLES`, including the Markdown styles. Verify no Material theme-role name remains in `src/afanes/ui/views` or `src/afanes/ui/components`, and the affected view tests pass.
- [x] 1.9 Update the hierarchy assertions in `tests/ui/test_theme.py` to compare the GNOME roles (`title-1` > `title-2` > `heading` > `body` > `caption`, weights 800/700/400). Verify `hatch test tests/ui/test_theme.py` passes.
- [x] 1.10 Verify the runtime resolves the platform font family on Linux, macOS, and Windows; if Flutter resolves to Roboto rather than the platform family, set the platform family explicitly or record the platform variation. Verify the no-bundled-font test still passes and the resolved family is documented.

## 2. Surfaces, selection, and action styles

- [x] 2.1 Point `components/panel.py`, the review card, the workspace sidebar, and the note view at the reference roles: window, sidebar, view, and secondary container. Verify with a view test that the card uses the view token, the sidebar uses the sidebar token, and the panel uses the secondary-container token.
- [x] 2.2 Set `SELECTED_ROW_COLOR` to the neutral selected-row token (10% `ON_SURFACE`), remove the 15% accent tint and the 3px accent edge, and keep the label and icon as the non-color cue. Verify with a theme test and a workspace test that selection is neutral and distinguishable.
- [x] 2.3 Make the filled-button style use `ACCENT_FILL` and `ON_ACCENT`, set the button and input corner radius from `CONTROL_RADIUS`, and remove the green action color. Verify with a theme test that the filled button background is the accent and that no action-color token remains.
- [x] 2.4 Add `DESTRUCTIVE_BUTTON_STYLE` from Red 3 (light) and Red 4 (dark) and apply it to the trash confirmation action and the trash header action in `views/page.py`. Verify with a test that both carry the destructive style and the Cancel control does not.
- [x] 2.5 Check the workspace at 1024x600 (the reference desktop minimum) and 1100x760 in both modes and adjust `SECTION_GAP`, `ITEM_GAP`, or `SIDEBAR_WIDTH` if a row clips. Verify by inspection and record the final values.
- [x] 2.6 Keep `SECTION_ICON_COLOR` on the muted role, make the active section use the neutral selected row, remove the accent icon and accent edge, and derive `LOG_ENTRY_TINT` and `LOG_ENTRY_DOT_COLOR` from the accent. Verify with a theme test that no per-section hue remains.
- [x] 2.7 Update the workspace and calendar views so inactive section icons share one tint, the active section uses the neutral selected row, and calendar marks use the accent. Verify with view tests for the neutral row and the accent marks.
- [x] 2.8 Update `tests/ui/test_workspace_view.py` and `tests/ui/test_calendar.py` for the neutral selection and monochrome icon treatment. Verify `hatch test tests/ui/test_workspace_view.py tests/ui/test_calendar.py` passes.
- [x] 2.9 Set splash, highlight, and hover to neutral `ON_SURFACE` shades and focus to the accent; set `visual_density` to the standard row rhythm. Verify with a theme test that hover and highlight are neutral, focus is accent, and density is standard.

## 3. Conformance gate

- [x] 3.1 Create `tests/ui/test_conformance.py` with a rule table and scanners for: color literals and `ft.Colors.*` outside `theme.py`, numeric layout literals outside `theme.py`, `ft.FilledButton` count, buttons carrying both `icon` and `content`/`text`/`label`, and `dense=True` occurrences. Verify the module imports and the scanners run over `src/afanes/ui`.
- [x] 3.2 Rebuild the embedded baseline for the strict tree: reference surface literals, remaining numeric layout literals, filled and destructive actions, icon-and-label buttons, dense rows, and Material theme-role names. Verify the gate passes with zero differences.
- [x] 3.3 Add the two failure directions: a synthetic source that exceeds a baseline count fails, and a baseline count above the actual count fails as stale. Verify both by unit tests on the scanner helpers.
- [x] 3.4 Add asset checks that no font file and no custom icon set is shipped under `src/`. Verify the check passes and fails against a temporary file in a fixture.
- [x] 3.5 Assert the four strict surface roles are pairwise distinct in both modes, the light note view is the brightest, and the dark note view is darker than the window and sidebar. Verify the tests pass.
- [x] 3.6 Shrink the baseline to match the tree after tasks 2.1-2.4 and 2.6-2.9, and confirm no new violation was introduced. Verify with `hatch test tests/ui/test_conformance.py`.
- [x] 3.7 Replace the typography rule with the strict rule: no `ft.TextStyle(size=` or `font_size` outside `theme.py`, and no Material `theme_style=` name in views or components. Verify the rule passes with an empty baseline and fails against a synthetic file.
- [x] 3.8 Add the icon rule: `ft.Icon` sizes come from `ICON_SIZE`/`ICON_SIZE_LARGE` tokens, no arbitrary literal is allowed, and every icon with an outlined variant uses it. Verify the rule passes and fails against a synthetic file.
- [x] 3.9 Add a token test that `WINDOW_MIN_WIDTH <= 1024` and `WINDOW_MIN_HEIGHT <= 600`, and verify the window at that size shows no clipped control.
- [x] 3.10 Add a theme and workspace test that the selected row uses the neutral token, not the accent tint, and that no accent edge is applied. Verify the tests pass.
- [x] 3.11 Change the filled/destructive and icon-and-label counts from module scope to view-class scope, so a module holding several dialogs is measured per view. Verify with a synthetic module that contains two view classes.

## 4. Documentation

- [x] 4.1 Rewrite `docs/develop/interface-standard.md` for strict conformance: pin libadwaita 1.8.0, list the reference surface, accent, destructive, and type tokens, state the neutral selection, limit the differences to the four Flet limits, correct the Flet attribution, and describe the relative type scale. Verify with `hatch run docs:build`.
- [x] 4.2 Update `docs/guide/workspace.md` and the four screenshots for the strict palette, neutral selection, and GNOME type scale; remove prose that describes the accent selection or the old neutral values. Verify the images show the reference surfaces and `hatch run docs:build` passes.
- [x] 4.3 Update `AGENTS.md` 4.6 to reference strict HIG conformance, the neutral navigation-sidebar selection, the GNOME type roles, and the four Flet limits. Verify the reference is present and the documented commands exist.
- [x] 4.4 Add the concrete HIG gaps and their waves to the standard page: max content width (wave 1), disabled-instead-of-error (wave 2), ellipsis, periods, and neutral tone (wave 3), banners-versus-toasts (wave 4), accessible names and keyboard (wave 5), adaptive breakpoints (wave 6), and placeholder pages and app icon (wave 7). Verify the page names each gap and `hatch run docs:build` passes.

## 5. Integration

- [x] 5.1 Run `hatch check` and fix lint, format, and type findings. Verify it exits clean.
- [x] 5.2 Run `hatch test --cover` and confirm coverage stays at or above 85% with the parser, link, and vault modules at 90%. Verify it exits clean.
- [x] 5.3 Run `openspec validate --all --strict` and `openspec doctor`, and run the vocabulary check from `AGENTS.md` 6.1. Verify all exit clean with no output from the grep commands.
- [x] 5.4 Review the built interface at 1024x600 and 1100x760 in light and dark mode and confirm each strict spec scenario is observable, including the neutral selection, reference surfaces, and GNOME type hierarchy; record any observed deviation in the change notes.

## Workflow follow-up

- Do not archive until every strict alignment task is checked and the gates pass again; the earlier landed commit is superseded.
- Archive the change after the maintainer approves the strict delivery.
- Run the post-archive release workflow from `AGENTS.md` 5.3; bump only if this archive completes a coherent milestone, otherwise keep the entry under `Unreleased`.
