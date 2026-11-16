# Proposal

## Why

Wave 7 is the last HIG conformance wave before `1.0.0`. The application still ships the toolkit's
default identity, fills empty views with plain muted text, and declares high-contrast mode a permanent
Flet limit even though Flet 1.1.2 reports the platform high-contrast flag. Finishing these gaps now
leaves the conformance baseline empty and narrows the bounded-differences list to real toolkit limits.

## What Changes

- Add one original SVG application icon and make the packaged Linux, macOS, and Windows builds use it.
  The icon is an identity asset, not an interface glyph, and contains no text, script, or external
  reference.
- Add a shared symbolic placeholder page for spaces that are empty but normally hold content: empty
  browser destinations, no search matches, empty Trash, and the detail region when no page is open. Each placeholder carries a heading, an optional guidance line, and at most one
  suggested action.
- Add light and dark high-contrast palettes. The application reads Flet's
  `SemanticsService.get_accessibility_features()` high-contrast flag at startup and on application
  resume, and selects the high-contrast palette when the platform reports it. Body text keeps at least
  7:1 contrast and boundaries stay visible.
- Remove high-contrast mode from the bounded-differences table, update the interface standard and
  guide references, and add conformance tests for the icon, placeholder structure, and both
  high-contrast palettes.
- Keep the conformance baseline empty; no new runtime dependency, network call, telemetry, or
  public-API removal.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `interface-theme`: adds the application identity icon, symbolic placeholder pages, and
  platform-driven high-contrast palettes; reduces the bounded-differences list by removing the
  high-contrast limit.

## Impact

Affected areas: `src/afanes/ui/theme.py`, `src/afanes/ui/app.py`, the workspace and page empty
states, the i18n UI catalogs, `src/assets/`, Flet build packaging, `tests/ui/`, `docs/develop/interface-standard.md`,
`docs/guide/workspace.md`, `README.md`, and `RELEASE.md`. No schema, vault format, CLI contract, or
dependency changes.
