# Tasks

## 1. Application identity icon

- [x] 1.1 Add `src/assets/icon.svg` as an original rounded mark with a page silhouette and check, a `viewBox`, and no text, script, external reference, or embedded raster; verify the SVG parses as XML and renders at 16 and 256 px.
- [x] 1.2 Add the icon asset test that rejects forbidden SVG elements, attributes, external URLs, and a missing viewBox; verify the test passes the new asset and fails a synthetic external reference.
- [x] 1.3 Verify Flet's icon resolver discovers `src/assets/icon.svg` and produces a platform image; record the result in `RELEASE.md` as an asset-only check until the native Linux toolchain can build an artifact.
- [x] 1.4 Document the application icon as an identity asset distinct from the interface glyph set in `docs/develop/interface-standard.md`; verify `hatch run docs:build` passes.

## 2. Symbolic placeholder pages

- [ ] 2.1 Add placeholder heading and guidance copy for an empty destination, empty search, empty Trash, and no-page detail to the English catalog and Spanish `.po`; classify each constant and verify `hatch test tests/i18n/test_copy.py` passes.
- [ ] 2.2 Add `ui/components/placeholder.py` with one monochrome icon, heading, optional guidance, and at most one suggested action; verify component tests cover structure, decorative icon, optional action, and accessible text.
- [ ] 2.3 Replace the workspace plain empty messages with the placeholder for an empty destination, no search matches, and empty Trash; verify workspace tests cover each heading, no duplicate header action, and hidden placeholders during a focused flow or owned banner.
- [ ] 2.4 Replace `PageView`'s no-page text with the placeholder and verify page tests cover the heading, guidance, and open-page suppression.
- [ ] 2.5 Update the workspace and interface-standard guidance for placeholder pages; verify `hatch run docs:build` passes.

## 3. Platform high contrast

- [ ] 3.1 Refactor `ui/theme.py` into a theme builder shared by standard and high-contrast palettes, add light and dark high-contrast palettes, and verify tests cover 7:1 body contrast, visible boundaries, focus, and hue-independent state.
- [ ] 3.2 Add `SemanticsService.get_accessibility_features()` detection to `AppShell` at startup and on application resume; verify tests cover true, false, and query-failure fallback without blocking the workspace.
- [ ] 3.3 Apply the selected high-contrast light and dark themes to `page.theme` and `page.dark_theme`; verify tests cover standard light, standard dark, high-contrast light, high-contrast dark, and resume.
- [ ] 3.4 Remove the high-contrast row from the bounded-differences table, update the count and accessibility notes, and verify `hatch run docs:build` and the conformance tests pass.

## 4. Final conformance and evidence

- [ ] 4.1 Run the real GNOME high-contrast setting at 1024x600 and 1100 px, in light and dark, across the destinations, page states, shortcut sheet, and date picker; record only observed results in `RELEASE.md` and leave the task open without that evidence.
- [ ] 4.2 Update the HIG wave 7 status, app icon row, placeholder-page behavior, and reduced bounded-differences list in `README.md`, `RELEASE.md`, and `docs/develop/interface-standard.md`; verify `hatch run docs:build` passes.
- [ ] 4.3 Run `hatch run render:check` and verify the standard 100%/200% layout still matches the snapshot after the placeholder and theme changes.

## 5. Integration checks

- [ ] 5.1 Run `hatch check` and verify lint, formatting, and strict types pass.
- [ ] 5.2 Run `hatch test --cover` and verify the suite passes at 85% coverage or higher.
- [ ] 5.3 Run `openspec validate --all --strict` and `openspec doctor`; verify both pass.
- [ ] 5.4 Run the vocabulary greps, `git diff --check`, and the tracked-`.mo` check; verify no prohibited matches, a clean diff, and no tracked compiled catalogs.
- [ ] 5.5 Run `hatch run docs:build` and verify the documentation build passes.

## Workflow follow-up

- Archive the change after review; the archive syncs the `interface-theme` delta.
- Run the post-archive release workflow in `AGENTS.md` 5.3. Assess whether wave 7 completes the `1.0.0` milestone once the Linux packaging evidence is available.
- Do not tag, push, or publish unless asked.
