# Proposal

## Why

The interface never chooses a visual identity: `ui/app.py` sets `ThemeMode.SYSTEM` but assigns no
theme, so Flet's defaults apply — a blue accent over an un-tinted neutral ramp. Every card, panel,
and sidebar surface uses the same neutral token, so the workspace reads as flat gray in light mode
and near-black in dark mode, with saturated blue only on selected rows and filled buttons. The app
has a deliberate information architecture but no visual hierarchy to match it, and its palette does
not yet read as the kind of tool it is. A familiar engineering-tool palette gives users a
reference they already know: a quiet neutral canvas, one blue accent, and restrained status hues.

## What Changes

- Assign an explicit application theme for both light and dark mode, replacing Flet's implicit
  default. The base follows a familiar engineering-tool canvas: white surfaces in light mode,
  `#0D1117`-like surfaces in dark mode.
- Adopt a familiar blue accent for links, selection, focus, and the active-section edge, plus a
  green action color for filled primary buttons.
- Keep the page, sidebar, cards, and panels white and separate them with 1 px boundaries; use a
  neutral fill for selected rows and a quiet neutral panel for steps.
- Give each browser section a quiet identity: a tinted leading icon plus an accent edge on the
  active entry. Section hues use the familiar attention, success, and done colors of engineering
  tools. Cards and content surfaces stay neutral; color never carries meaning alone.
- Strengthen typographic hierarchy within one sans family — size, weight, spacing, and color —
  without bundling a new font.
- Keep the note canvas white in light mode and use a warm attention surface for the due-work notice.
- Let the Markdown body editor fill the page pane in edit and raw modes instead of staying at a
  fixed line count.
- Move the vault path and vault actions into a compact status bar along the bottom, and drop the
  static app-name heading; the window title and page titles already identify the app.
- Keep both theme modes first-class: every token is defined for light and dark, and contrast is
  checked in each.
- Regenerate the documentation screenshots so the guides show the new palette and layout.

## Capabilities

### New Capabilities

- `interface-theme`: how the application chooses its colors, surfaces, accents, and typographic
  hierarchy for the desktop and browser presentations, including light/dark parity and
  accessible contrast.

### Modified Capabilities

None. No existing capability describes appearance; `app-runtime` covers launch, presentation, and
session behavior only.

## Impact

- `src/afanes/ui/theme.py`: theme constants (light/dark theme objects or their seeds and surface
  policy), neutral surface roles, border and accent tokens, and the section-to-color mapping.
- `src/afanes/ui/app.py`: assigns the light and dark themes during page configuration.
- `src/afanes/ui/views/workspace.py`: applies section icon tints and the active-entry edge marker.
- `src/afanes/ui/views/`, `src/afanes/ui/components/`: replace flat neutral choices with the
  layered tokens where hierarchy is missing today.
- `tests/ui/`: asserts the shell applies a theme in both modes and that views use theme tokens
  rather than literal colors.
- `docs/guide/workspace.md`: a short appearance note.
- `docs/_static/screenshots/`: regenerated workspace, project page, processing, and review images.
- No dependency, vault format, storage, or network impact.
