# Tasks

## 1. HIG app icon

- [x] 1.1 Replace `src/assets/icon.svg` with the 128×128 HIG-template drawing from `design.md`:
  a 104×104 baseplate with a 4 px darker front profile, the page-and-check mark, and only GNOME
  palette colors. Verify the SVG parses as XML and its `viewBox` is `0 0 128 128`, with every
  coordinate on the 2 px grid inside `12…116`.
- [x] 1.2 Extend `tests/test_assets.py` with the canvas, safe-area, 2 px-grid, palette-membership,
  front-darker-than-top, and fold/check contrast checks, plus synthetic failures for a full-bleed
  tile, an odd coordinate, a non-palette color, and a too-light fold. Verify
  `hatch test tests/test_assets.py` passes.
- [ ] 1.3 Load the new SVG through `flet_platform_assets.load_source` at 2048 px and render the
  Linux, Windows, macOS, and web sets. Verify there are no unexpected warnings, then inspect the
  rendered icon at 16, 32, 64, 128, and 256 px on light and dark backgrounds; confirm the page,
  fold, and check remain visible at 32 px and the front profile is visible at 128 and 256 px.

## 2. Documentation

- [ ] 2.1 Update the icon section of `docs/develop/interface-standard.md` to describe the HIG
  template, the top/front depth, the palette-only colors, and the 32 px legibility contract while
  keeping the identity-asset/interface-glyph distinction. Verify `hatch run docs:build` passes.
- [ ] 2.2 Update the application icon evidence in `RELEASE.md` with the new source, the rendered
  platform sets, the small-size light/dark result, and the existing native-Linux-artifact caveat.
  Verify the recorded version, date, and sizes match the render that was actually run.
- [ ] 2.3 Add the behavior to `CHANGELOG.md` under `Unreleased` → `Changed`, naming this OpenSpec
  change and recording that no runtime dependency or public API changed. Verify the entry renders
  correctly and the `Unreleased` heading remains.

## 3. Integration checks

- [ ] 3.1 Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`,
  `openspec doctor`, and the two vocabulary compliance greps. Verify every command passes.
- [ ] 3.2 Review the final diff with `git status --short` and `git diff --stat`. Verify only the
  icon asset, `tests/test_assets.py`, the interface standard, `RELEASE.md`, `CHANGELOG.md`, and the
  OpenSpec change files changed; no runtime code, vault behavior, dependency, or public API changed.

## Workflow follow-up

- Archive the change after review and sync the `interface-theme` delta into the main spec.
- When the Linux build toolchain is available, build the native artifact and verify the packaged
  icon at 32, 64, 128, and 256 px on light and dark; record that release-gate evidence in
  `RELEASE.md`. This is not a task for this change because the toolchain is absent.
- A symbolic app-icon variant remains a separate packaging change; this change deliberately ships
  only the full-color icon.
