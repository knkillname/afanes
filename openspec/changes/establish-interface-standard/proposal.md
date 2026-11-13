# Proposal

## Why

The interface reads flat because its three structural roles — page, sidebar, card — resolve
to the same surface color, so the only separation is a 1px border; on top of that one theme
object serves both light and dark mode, and the palette mixes a GitHub blue seed, a GitHub
green action, and four unrelated section hues. The maintainer wants the visual identity to
follow the GNOME Adwaita design language from now on, which requires a standard that is
enforced continuously rather than a one-off restyle.

## What Changes

- Replace the palette, action, and selection requirements in `interface-theme` with a
  layered model: three distinct surface roles per mode, an explicitly defined light palette
  and dark palette, and a single accent that supplies both fills and a contrast-checked
  text variant.
- **BREAKING** (visual identity): the separate green action color is removed — suggested
  actions use the accent; browser selection moves from a neutral fill to an accent tint;
  existing screenshots and documented colors become stale.
- Retire the four per-section icon hues: section icons become monochrome, the active section
  uses the accent, and log marks use the accent. This removes the existing browser-section
  requirement and replaces it, because a four-hue chrome identity contradicts the reference
  language. Previous spec text is not treated as binding where it conflicts with strict
  adherence.
- Add a declarative conformance ratchet: the build fails on new violations of the standard,
  and a baseline of existing exceptions may only shrink. The baseline is a debt ledger, not a
  permanent exemption, and it must reach empty before the standard is complete.
- Replace the hard-coded text styles with one text theme and the standard style roles. The
  typography guideline forbids per-control font sizes, and five sites set one today.
- Declare and bound the differences from the reference language: the platform typeface is the
  guideline-preferred choice; the monochrome interface icon set and the toolkit's widget rendering
  are toolkit realities; access-key mnemonics and a high-contrast style are unavailable in the
  toolkit. A new difference requires its own spec change.
- Record the remaining migration as sequenced waves in `design.md`; this change lands wave 0
  (tokens, palettes, surfaces, selection, action styles, monochrome section treatment, text theme,
  gate) only. Waves are ordering, not exemptions: the target is strict conformance. The writing-style
  and keyboard/accessibility gaps are named waves, not omissions.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `interface-theme`: palette, contrast, accent/action, and surface requirements are replaced;
  the browser-section tint requirement is removed and replaced by a monochrome icon treatment;
  the typography requirement moves hierarchy onto the named text-theme roles; a conformance-ratchet
  requirement is added; the requirement bounding differences from the reference language is widened
  to cover access keys and high contrast.

## Impact

- `src/afanes/ui/theme.py` (palettes, roles, radii, spacing, retired section hues, text theme),
  `src/afanes/ui/app.py` (light and dark theme assignment), `src/afanes/ui/components/panel.py`,
  `src/afanes/ui/components/calendar.py`, `src/afanes/ui/components/log_tree.py`, and
  `src/afanes/ui/views/workspace.py` (surface roles, selection, monochrome section icons and
  log marks), plus the six view and component files that reference the retired text-style
  constants.
- `tests/ui/test_theme.py` (assertions change) and a new conformance gate under `tests/ui/`
  with a checked-in baseline.
- `docs/develop/` gains the interface standard; `docs/guide/` screenshots and any prose that
  names the old colors or the neutral selection must be refreshed.
- No runtime dependency, vault, CLI, or data-model change. Tk/desktop and web presentations
  share the same tokens, so platform parity is preserved.
