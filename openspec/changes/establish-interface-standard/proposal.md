# Proposal

## Why

The first wave of the interface standard claimed strict Adwaita adherence, but it mixed pre-1.8
Adwaita neutrals with Material text roles and an accent selection. The delivered palette, type
scale, and selected-row treatment therefore do not match the reference implementation. The
maintainer wants strict adherence to the GNOME Human Interface Guidelines, which requires
correcting the standard and the landed wave before it is archived.

## What Changes

- Adopt the libadwaita 1.8.0 reference tokens exactly: window, view, sidebar, header bar,
  secondary container, body and muted text, accent fill and text, and destructive color.
- **BREAKING** (second visual pass): replace the pre-1.8 neutrals; return selection to the
  neutral navigation-sidebar treatment; move the page and step hierarchy onto the Adwaita title
  scale; use Red 3 for the light destructive fill. The previously regenerated screenshots,
  documented colors, and selection assertions become stale again.
- Replace the Material text-theme vocabulary with the GNOME standard styles: `title-1` through
  `title-4`, `heading`, `body`, `caption`, and `caption-heading`, expressed as relative
  percentages of an 11 pt-equivalent base rather than per-control sizes.
- Use symbolic/outlined interface icons at token sizes. The toolkit's Material icon set remains
  the one asset-free icon difference; no custom SVG set is bundled.
- Narrow the declared differences to the genuine Flet limits: the Material icon set, the
  toolkit's widget rendering, the absent access-key mnemonics, and the absent high-contrast
  input. The platform typeface is guideline-required, not a difference. Correct the
  high-contrast and mnemonic attribution from Flutter to Flet.
- Extend the conformance gate to the strict rules: neutral selection, reference surface tokens,
  GNOME text roles, icon sizes, the 1024x600 minimum window, and one suggested or destructive
  style per view.
- Keep wave 0 as the scope, but name the remaining HIG gaps in their waves: max content width
  (wave 1), disabled-instead-of-error (wave 2), ellipsis, periods, and neutral tone (wave 3),
  banners-versus-toasts (wave 4), accessible names and keyboard (wave 5), adaptive breakpoints
  (wave 6), placeholder pages and app icon (wave 7).
- Record that the landed commit is superseded. The change MUST NOT be archived until the strict
  alignment tasks are checked and the gates pass again.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `interface-theme`: the palette, contrast, surface, selection, accent/action, typography,
  icon, and conformance-ratchet requirements move from a bounded Adwaita interpretation to
  strict Adwaita 1.8.0 conformance with only the genuine Flet toolkit limits declared. The
  browser-section tint requirement stays removed; its replacement now uses the neutral selected
  row instead of an accent tint.

## Impact

- `src/afanes/ui/theme.py` (reference tokens, neutral selection, GNOME type roles, radii, icon
  sizes, minimum window), `src/afanes/ui/app.py` (theme assignment and minimum window),
  `src/afanes/ui/components/panel.py`, `src/afanes/ui/components/calendar.py`,
  `src/afanes/ui/components/log_tree.py`, and `src/afanes/ui/views/workspace.py` (surfaces,
  neutral selection, monochrome icons, log marks), plus the views that reference the text roles
  and icon sizes.
- `tests/ui/test_theme.py`, `tests/ui/test_app.py`, `tests/ui/test_workspace_view.py`,
  `tests/ui/test_calendar.py`, and the conformance baseline in
  `tests/ui/test_conformance.py`.
- `docs/develop/interface-standard.md`, `docs/guide/workspace.md`, and all four screenshots
  under `docs/_static/screenshots/`.
- No runtime dependency, vault, CLI, or data-model change.
