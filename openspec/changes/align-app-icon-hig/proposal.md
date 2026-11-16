# Proposal

## Why

The application identity icon is the last visible part of the interface that does not follow the
GNOME app-icon guidance. The current mark is a flat, full-bleed rounded tile with a 28 px corner
radius at 128 px, non-palette secondary shades, and a fold detail that is only 1.26:1 against the
page and disappears at small sizes. It reads more like a mobile app tile than a GNOME application
icon. The project already claims strict HIG conformance for the interface, so the identity asset
should follow the same reference before the `1.0.0` release gate.

## What Changes

- Replace `src/assets/icon.svg` with a full-color icon drawn on the GNOME Human Interface Guidelines
  app-icon template: a 128×128 canvas, the template's 2 px grid, and the bottom baseline.
- Keep the page-and-check metaphor, but give the mark the HIG top-and-front depth profile, with the
  front surface darker than the top surface.
- Use only the GNOME palette for the icon's fills and strokes. Remove the full-bleed tile and the
  low-contrast fold tint; keep the silhouette within the template's visual weight and safe area.
- Keep the icon self-contained: no text, script, external reference, or embedded raster image.
- Make the small-size result explicit: the page, fold, and check remain legible at 32 px, and the
  silhouette remains recognizable from 16 to 256 px on light and dark backgrounds.
- Extend `tests/test_assets.py` to guard the 128 px canvas, palette-only colors, artwork bounds, and
  the absence of a full-bleed tile, in addition to the existing self-containment checks.
- Update the icon section of `docs/develop/interface-standard.md` and the asset evidence in
  `RELEASE.md`, and add a manual light/dark render check at 16, 32, 64, 128, and 256 px.

**Non-goals**

- Adding a symbolic app-icon variant. The Flet build exposes one application-icon slot per platform,
  so a symbolic asset would need its own Linux packaging change. The full-color icon remains the
  only identity asset in this change.
- Changing the interface glyph set, the window presentation, or any vault behavior.
- Adding a runtime dependency, network access, or a new asset format.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `interface-theme`: a new requirement now covers the GNOME app-icon template geometry, palette
  colors, depth treatment, and small-size legibility; the existing self-containment and
  identity-asset separation rules remain.

## Impact

- `src/assets/icon.svg` is replaced; the Flet icon resolver continues to discover it and generate
  the Linux, Windows, macOS, and web icon sets.
- `tests/test_assets.py` gains deterministic checks for the new geometry and palette contract.
- `docs/develop/interface-standard.md` and `RELEASE.md` record the icon treatment and the
  asset-only packaging evidence.
- No runtime code, public API, vault format, database, dependency, or user-facing copy changes.
- The symbolic app-icon gap is documented as a later packaging concern, not silently claimed as
  conformant.
