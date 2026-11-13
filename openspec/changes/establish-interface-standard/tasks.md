# Tasks

## 1. Palette and tokens

- [x] 1.1 Add the light and dark palette values to `src/afanes/ui/theme.py`: three surface roles, `SURFACE_CONTAINER_COLOR`, `ACCENT_FILL`, `ACCENT_TEXT`, `ON_ACCENT`, `DESTRUCTIVE`, text, muted text, border, notice, and status roles. Verify with a token test that every required role exists and that the light and dark tables are distinct.
- [x] 1.2 Replace `CARD_RADIUS` with `SURFACE_RADIUS = 12` and add `CONTROL_RADIUS = 8`; move spacing to `ITEM_GAP = 12`, `SECTION_GAP = 18`, `PAGE_PADDING = 24`. Verify with a token test that the new names exist and the old name is gone.
- [x] 1.3 Build `LIGHT_THEME` and `DARK_THEME` as separate `ft.Theme` objects with explicit `ft.ColorScheme` values and `surfaces=ft.ThemeSurfaces.NEUTRAL`; remove the shared `THEME`. Verify with a test that both expose a `color_scheme`, that they are different objects, and that `THEME` no longer exists.
- [x] 1.4 Assign `page.theme = LIGHT_THEME` and `page.dark_theme = DARK_THEME` in `src/afanes/ui/app.py`, and keep the page background on `PAGE_SURFACE_COLOR`. Verify in `tests/ui/test_app.py` that the two assignments are distinct and the background token is used.
- [x] 1.5 Add WCAG contrast assertions to the token tests: body text, muted text, and accent text meet 4.5:1 on their surface in both modes; accent fill, icons, and control boundaries meet 3:1. Verify the computed ratios pass for the values from 1.1.
- [x] 1.6 Update the existing assertions in `tests/ui/test_theme.py` that pin `ACTION_COLOR`, `SELECTED_ROW_COLOR`, and `CARD_RADIUS`. Verify `hatch test tests/ui/test_theme.py` passes.
- [x] 1.7 Add `TEXT_THEME = ft.TextTheme(...)` to `theme.py` with the standard roles, weights, and colors, and attach it to both palettes. Verify with a test that every role used by the views resolves through the theme.
- [x] 1.8 Replace `PAGE_TITLE_TEXT_STYLE`, `STEP_HEADLINE_TEXT_STYLE`, `SECTION_LABEL_TEXT_STYLE`, `METADATA_TEXT_STYLE`, and the inline style in `views/projects.py` with `theme_style=ft.TextThemeStyle.<role>` at their call sites. Verify no `TextStyle(size=` remains outside `theme.py` and the affected view tests pass.
- [x] 1.9 Update the hierarchy assertions in `tests/ui/test_theme.py` to compare the text-theme roles instead of the removed style constants. Verify `hatch test tests/ui/test_theme.py` passes.

## 2. Surfaces, selection, and action styles

- [x] 2.1 Point `components/panel.py`, the review card, and the workspace sidebar at the page, region, card, and container roles instead of one shared surface. Verify with a view test that a built card uses `CARD_SURFACE_COLOR` and the sidebar uses `REGION_SURFACE_COLOR`.
- [x] 2.2 Set `SELECTED_ROW_COLOR` to a 15% accent tint and keep the 3px accent edge on the active section. Verify with a theme test for the tinted selected color and a workspace test that the edge container is still present.
- [x] 2.3 Make the filled-button style use `ACCENT_FILL` and `ON_ACCENT`, set the button and input corner radius from `CONTROL_RADIUS`, and remove the green action color. Verify with a theme test that the filled button background is the accent and that no action-color token remains.
- [x] 2.4 Add `DESTRUCTIVE_BUTTON_STYLE` and apply it to the trash confirmation action and the trash header action in `views/page.py`. Verify with a test that the confirm control carries the destructive style and the Cancel control does not.
- [x] 2.5 Check the workspace at 1100x760 and 960x640 in both modes and adjust `SECTION_GAP`, `ITEM_GAP`, or `SIDEBAR_WIDTH` if a row clips. Verify by inspection and record the final values in the task commit message.
- [x] 2.6 Replace the four section-hue constants with `SECTION_ICON_COLOR` using the muted text role, collapse `REVIEW_SECTION_COLOR` into the accent, and derive `LOG_ENTRY_TINT` and `LOG_ENTRY_DOT_COLOR` from the accent. Verify with a theme test that no per-section hue constant remains.
- [x] 2.7 Update the workspace and calendar views so inactive section icons share one tint, the active section uses the accent in its icon, edge, and row, and calendar marks use the accent. Verify with view tests that inactive icons share a tint, the active section uses the accent, and the calendar marks use the accent tint.
- [x] 2.8 Update `tests/ui/test_workspace_view.py` and `tests/ui/test_calendar.py` assertions for the monochrome section treatment. Verify `hatch test tests/ui/test_workspace_view.py tests/ui/test_calendar.py` passes.
- [x] 2.9 Replace Material's default ink feedback by setting the theme's splash, highlight, hover, and focus colors from the accent roles, and set `visual_density` to the standard's row rhythm. Verify with a theme test that all four feedback colors resolve to token values rather than toolkit defaults.

## 3. Conformance gate

- [x] 3.1 Create `tests/ui/test_conformance.py` with a rule table and scanners for: color literals and `ft.Colors.*` outside `theme.py`, numeric layout literals outside `theme.py`, `ft.FilledButton` count per view module, buttons carrying both `icon` and `content`/`text`/`label`, and `dense=True` occurrences. Verify the module imports and the scanners run over `src/afanes/ui`.
- [x] 3.2 Add the embedded baseline for the violations measured on the current tree: 76 numeric layout literals across 11 files, 37 filled buttons, 31 icon-and-label buttons, 14 dense rows. Verify the gate passes with zero differences on the unmodified tree.
- [x] 3.3 Add the two failure directions: a synthetic source that exceeds a baseline count fails, and a baseline count above the actual count fails as stale. Verify both by unit tests on the scanner helpers.
- [x] 3.4 Add asset checks that no font file and no custom icon set is shipped under `src/`. Verify the check passes and fails against a temporary file in a fixture.
- [x] 3.5 Add tests asserting the three surface roles differ pairwise in both modes and that the note canvas is the brightest light surface. Verify the tests pass and would have failed on the old single-surface theme.
- [x] 3.6 Shrink the baseline to match the tree after tasks 2.1-2.4, and confirm no new violation was introduced. Verify with `hatch test tests/ui/test_conformance.py`.
- [x] 3.7 Add the typography rule: no `ft.TextStyle(size=` or `font_size` outside `theme.py`. Verify the rule passes with an empty baseline after task 1.8 and fails against a synthetic file that hard-codes a size.

## 4. Documentation

- [x] 4.1 Add `docs/develop/interface-standard.md` and its `develop/interface-standard` entry in the `docs/index.md` toctree, describing the five conformance levels, the bounded differences table (typeface, icons, widget rendering, access keys, high contrast), the monochrome section treatment, the text-theme roles, the gate and baseline ratchet, and the migration waves. Verify with `hatch run docs:build`.
- [x] 4.2 Update the guide pages and `docs/guide/workspace.md` where they describe the old palette, the neutral selection, or per-section icon tints, and regenerate the four screenshots in `docs/_static/screenshots/`. Verify each image shows the new surfaces, monochrome icons, and text hierarchy, and that `hatch run docs:build` still passes.
- [x] 4.3 Add the interface standard and the conformance gate to `AGENTS.md` section 4.6 as the durable reference for future work, state that the section-tint requirement is retired, and record that control labels move to header capitalization in the writing-style wave. Verify the reference is present and the documented commands exist.

## 5. Integration

- [x] 5.1 Run `hatch check` and fix lint, format, and type findings. Verify it exits clean.
- [x] 5.2 Run `hatch test --cover` and confirm coverage stays at or above 85% with the parser, link, and vault modules at 90%. Verify it exits clean.
- [x] 5.3 Run `openspec validate --all --strict` and `openspec doctor`, and run the vocabulary check from `AGENTS.md` 6.1. Verify all exit clean with no output from the grep commands.
- [x] 5.4 Review the built interface in light and dark mode at both window sizes and confirm each spec scenario is observable, including the text-theme hierarchy; record any observed deviation in the change notes.

## Workflow follow-up

- Archive the change after the maintainer approves the delivered wave.
- Run the post-archive release workflow from `AGENTS.md` 5.3; bump only if this archive completes a coherent milestone, otherwise keep the entry under `Unreleased`.
