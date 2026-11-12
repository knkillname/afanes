# Tasks

## 1. Theme definition and shell assignment

- [x] 1.1 Add `THEME_SEED` (engineering-tool accent blue `#0969DA`) and a `THEME = ft.Theme(color_scheme_seed=THEME_SEED, surfaces=ft.ThemeSurfaces.TONAL)` constant to `src/afanes/ui/theme.py`, keeping the module's Flet-only imports; verify `hatch run pytest tests/core/test_architecture.py` passes.
- [x] 1.2 Assign `page.theme = afanes.ui.theme.THEME` and `page.dark_theme = afanes.ui.theme.THEME` in `_Shell._configure` while keeping `ThemeMode.SYSTEM`; add `theme`/`dark_theme` attributes to `FakePage` in `tests/ui/test_app.py`; verify `hatch run pytest tests/ui/test_app.py` passes.
- [x] 1.3 Extend the shell test to assert `theme_mode` is `SYSTEM` and both theme slots hold the theme constant; verify the new assertions fail when either assignment is removed.
- [x] 1.4 Add the green action color through the filled-button theme and the neutral selected-row fill through the list-tile theme; verify a theme test asserts both are configured.

## 2. Surface depth stack

- [x] 2.1 Define `PAGE_SURFACE_COLOR`, `REGION_SURFACE_COLOR`, and `CARD_SURFACE_COLOR` as the white canvas/sidebar/note surfaces, plus `SELECTED_ROW_COLOR`, the 1 px `BORDER_COLOR`, and keep `SURFACE_CONTAINER_COLOR` as an alias; verify `hatch run pytest tests/ui` still passes.
- [x] 2.2 Apply `REGION_SURFACE_COLOR` to the workspace sidebar, `CARD_SURFACE_COLOR` to `Card`, `Panel`, and the existing card containers in `views/page.py`, `views/processing.py`, `views/review.py`, and `app.py`, and `PAGE_SURFACE_COLOR` to the page background, adding the 1 px border to each; verify each affected view test still passes.
- [x] 2.3 Assert the surface stack in tests: the page background and sidebar use their region tokens, cards use the card token, and both carry the border; verify `hatch run pytest tests/ui/test_workspace_view.py tests/ui/test_project_body_view.py` passes.
- [x] 2.4 Move the vault path, refresh action, and vault menu into a bottom status bar and remove the static app-name heading; verify `hatch run pytest tests/ui/test_workspace_view.py` passes and the status bar keeps the actions reachable.
- [x] 2.5 Apply the warm notice surface to the launch digest and assert it in the digest test; verify `hatch run pytest tests/ui/test_app.py` passes.
- [x] 2.6 Make the Markdown body editor and raw rescue field fill the page pane by hiding the read column while editing and expanding the editor; verify the edit and raw view tests assert the expanded layout.
- [x] 2.7 Change the step card to the quiet neutral surface with normal text and add the 1 px boundary; verify `hatch run pytest tests/ui/test_project_body_view.py` passes.

## 3. Section identity

- [x] 3.1 Add `INBOX_SECTION_COLOR`, `PROJECTS_SECTION_COLOR`, `REFERENCES_SECTION_COLOR`, and `REVIEW_SECTION_COLOR` constants to `theme.py` using familiar attention, success, done, and accent hues, without importing `afanes.ui.state`; verify `hatch run pytest tests/core/test_architecture.py` passes.
- [x] 3.2 Map the section enum to those constants in `views/workspace.py` next to `_SECTION_ICONS` and tint only each section tile's leading icon; verify a workspace test asserts four distinct icon colors and that review uses the accent.
- [x] 3.3 Mark the active section with a 3 px accent edge in addition to the existing `selected` state; verify a workspace test asserts the edge appears only on the active tile.
- [x] 3.4 Confirm section colors are confined to leading icons and that labels, note rows, and borders never use them; verify by inspecting every `_SECTION_ICONS` usage and noting the result in the task commit.

## 4. Typography and appearance documentation

- [x] 4.1 Add page-title, section-label, and metadata `ft.TextStyle` constants to `theme.py` using size, weight, and color only, and leave `THEME.font_family` unset; verify a test asserts `THEME.font_family is None` and that the three styles differ.
- [x] 4.2 Apply the new styles to the page title, sidebar group labels, and metadata text, and retire the static app-name heading; verify `hatch run pytest tests/ui/test_page_view.py tests/ui/test_workspace_view.py` passes.
- [x] 4.3 Add an Appearance section to `docs/guide/workspace.md` describing system light/dark following, the single blue accent, section icon tints, and the layered surfaces; verify `hatch run docs:build` passes.

## 5. Integration checks

- [x] 5.1 Run the desktop interface in light and dark system mode, check body text 4.5:1 and large text, icons, boundaries 3:1, and record the observed result; verify no generated pair needs an override, or add the override constant and re-check.
- [x] 5.2 Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, and `openspec doctor`; verify all pass before reporting the change complete.

## 6. Documentation screenshots

- [x] 6.1 Regenerate `workspace.png`, `project-page.png`, `processing.png`, and `review.png` in light mode with the new palette; verify each image matches its alt text and shows the white surfaces, blue selection, and green primary actions.
- [x] 6.2 Verify `hatch run docs:build` passes and every screenshot reference resolves.

## Workflow follow-up

- Commit each task as it goes green, with a subject naming the behavior.
- Run the archive workflow only after review; the release step in `AGENTS.md` section 5.3 follows the archive.
