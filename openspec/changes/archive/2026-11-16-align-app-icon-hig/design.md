# Design

## Context

See `proposal.md` for motivation. The current `src/assets/icon.svg` is a 256×256 SVG with a 240×240
rounded tile, a 28 px corner radius at 128, no depth, and two non-palette shades. Flet reads the SVG
through `flet_platform_assets`, renders it at 2048 px, and produces the Linux hicolor tree (16–512),
the Windows ICO (16, 32, 48, 256), the macOS app-icon set (16–1024), and the web icons. The asset
test currently checks only XML validity, `viewBox` presence, forbidden elements, and external
references.

The HIG app-icon template is a 128×128 canvas with a 2 px grid, a safe area, a bottom baseline, a
top/front depth treatment, and the GNOME palette. Flet exposes one full-color icon slot per platform
and no symbolic app-icon slot; the symbolic variant is deliberately outside this change.

## Goals / Non-Goals

**Goals:**

- Replace the mark with a full-color 128×128 HIG-template icon that keeps the page-and-check metaphor.
- Give the mark a smaller, squarer baseplate and a darker front profile instead of the current
  full-bleed mobile-style tile.
- Use only GNOME palette colors, with enough contrast that the fold and check survive at 32 px.
- Make the asset contract deterministic: canvas, safe-area bounds, 2 px grid, palette membership,
  depth, and contrast are checked by `tests/test_assets.py`.
- Preserve Flet discovery and the existing cross-platform icon pipeline.

**Non-Goals:**

- A symbolic app-icon variant or a Linux packaging hook. Flet has one icon slot per platform; that
  work belongs in a separate change.
- A nightly icon variant, a new icon format, or a custom interface glyph set.
- Changing the window, the interface layout, or any vault behavior.
- Claiming that the native Linux artifact is verified; the build toolchain is still absent.

## Decisions

### Canvas and artwork geometry

Use `viewBox="0 0 128 128"` and draw all geometry on the template's 2 px grid. The artwork uses the
template's square guide as its visual weight:

| Element | Geometry at 128 px | Fill |
| --- | --- | --- |
| Baseplate front | `x=12`, `y=12`, `w=104`, `h=104`, radius 8 | Blue 5 |
| Baseplate top | `x=12`, `y=12`, `w=104`, `h=100`, radius 8 | Blue 4 |
| Page | `x=32`, `y=16`, `w=64`, `h=88`, with the top-right 16×16 corner cut away | Light 1 |
| Fold | triangle `(80,16)`, `(96,32)`, `(80,32)` filling the cut corner | Blue 3 |
| Check | `(48,72)` → `(60,84)` → `(84,56)`, stroke 8, round caps and joins | Blue 5 |

The baseplate is 104×104 (81.25% of the 128 canvas), not a 120×120 full-bleed tile. Its 4 px front
band is visible below the 100 px top surface, so the mark has the HIG top/front profile while the
overall silhouette stays square for macOS's pre-shaped-icon handling. The page and check sit inside
the top surface; the check remains 2 px wide at 32 px and the fold remains 4 px square.

All coordinates stay within `12…116` and are even. That is the deterministic expression of “inside
the template safe area, on the 2 px grid, not edge to edge.” The 12 px margin matches the template's
square guide (approximately 103×103 centered on 128).

### Palette and contrast

Use only GNOME palette values:

- Blue 4 `#1C71D8` for the top surface;
- Blue 5 `#1A5FB4` for the front profile and the check;
- Blue 3 `#3584E4` for the fold;
- Light 1 `#FFFFFF` for the page.

Blue 5 on white is about 6.3:1, and Blue 3 on white is about 3.8:1, so the check and fold survive at
32 px. Blue 4 on the light and dark reference backgrounds (Light 1 and Dark 5) is about 4.77:1 and
4.40:1 respectively. The front profile is darker than the top surface but intentionally subtle
(about 1.3:1 between Blue 5 and Blue 4), matching the HIG's “front” treatment. No gradient is used:
straight surfaces keep flat colors.

Alternative considered: keep `#0B4F9E` for the check. Rejected because it is outside the HIG palette;
Blue 5 gives enough contrast without a custom shade. Alternative considered: keep the light
`#D7E6FC` fold. Rejected because it is 1.26:1 against the page and disappears at 32 px.

### Asset contract in `tests/test_assets.py`

Extend the existing asset test rather than add a second asset-testing module. The test is a pure
function over the tracked SVG source, so it stays fast and deterministic:

1. Parse the root and require `viewBox="0 0 128 128"`.
2. Keep the existing forbidden-element, external-reference, and no-raster checks.
3. Walk `rect`, `path`, `polygon`, `line`, and `circle` geometry; require every numeric coordinate
   to be even and inside `12…116` (with `width`/`height` counted from the element's origin).
4. Collect every `fill`, `stroke`, and `stop-color`; require each color to be a GNOME palette value
   or `none`.
5. Look up the `top`, `front`, `page`, `fold`, and `check` elements; require the front fill to be
   darker than the top fill, and require the fold/page and check/page contrast ratios to be at least
   3:1.
6. Add synthetic failing cases for a full-bleed rectangle, an odd coordinate, a non-palette color,
   and a fold that is too light. The existing synthetic failures for external references and rasters
   stay.

The geometry check is deliberately broader than one exact drawing: a future icon may move or resize
the page as long as it stays on the grid, inside the safe area, and keeps the contrast contract. A
test that asserted exact path strings would make every visual adjustment a test rewrite.

### Flet pipeline and documentation

Keep the filename `src/assets/icon.svg`; Flet resolves it automatically. Rebuilding invalidates the
`build/.hash/icons` stamp through the source mtime; if a stale icon appears, delete that stamp and
rebuild. The existing `render_icons` evidence path is reused: load the SVG at 2048 px, render the
Linux, Windows, macOS, and web sets, and record the warnings. This remains asset-only evidence until
the Linux native toolchain produces an artifact.

Update the icon section of `docs/develop/interface-standard.md` to describe the HIG-template,
top/front, palette, and 32 px contract. Keep the existing identity-asset/interface-glyph distinction.
Update `RELEASE.md` with the new render evidence and the native-artifact caveat. Add the behavior to
`CHANGELOG.md` under `Unreleased`; the release workflow moves it later. `README.md` needs no change
because installation, features, and screenshots are unaffected.

## Risks / Trade-offs

- **HIG style is partly subjective.** The tests prove canvas, palette, bounds, depth, and contrast,
  not “looks GNOME.” Mitigation: render at 32, 64, 128, and 256 px, compare against the HIG template,
  and record the manual check in `RELEASE.md`.
- **The 4 px front profile is only 1 px at 32 px.** It may read as a slightly darker bottom edge
  rather than depth. Mitigation: keep the profile visible at 128 and 256; do not add a stronger
  shadow or a second outline that would violate the HIG's flat-surface preference.
- **The 104×104 baseplate is close to macOS's pre-shaped threshold.** Flet may keep it as-is instead
  of applying the macOS grid. That is acceptable because 104/128 is 81.25%, close to the 80.5% macOS
  grid; the square silhouette avoids a second inset. The existing release evidence already records
  macOS's pre-shaped behavior for the current icon.
- **The palette test can block a future deliberate color.** That is the point of the change; a new
  color needs a spec/asset decision, not an incidental edit.
- **The native artifact is still unverified.** The change can prove the source and the asset-only
  render, not the packaged Linux icon. `RELEASE.md` must keep that caveat until the toolchain builds
  the platform artifact.

## Migration Plan

Replace the SVG, tests, and docs in one scoped commit. There is no data migration and no runtime
state. If the visual review rejects the drawing, adjust the geometry within the safe area and rerun
the asset test; if the whole approach is rejected, revert the asset and its tests/docs together. The
previous icon remains in Git history. Flet's generated icon sets are build artifacts and are not
committed; the stale-stamp note above is the only build-cache action.
