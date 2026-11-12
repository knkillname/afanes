# Design

## Context

See `proposal.md` for motivation and `specs/interface-theme/spec.md` for the behavior contract.

The current theme layer is a set of constants in `src/afanes/ui/theme.py` aliasing Material roles
(`SURFACE_CONTAINER_LOW`, `ON_SURFACE`, `OUTLINE_VARIANT`, `SECONDARY_CONTAINER`). `ui/app.py`
sets `ThemeMode.SYSTEM` and nothing else, so Flet generates its default scheme: blue seed, neutral
(un-tinted) surfaces. Because every structural container reuses `SURFACE_CONTAINER_LOW`, the page
and all its cards sit on nearly the same gray step.

Constraints that shape the approach:

- `theme.py` is declared an import leaf by `tests/core/test_architecture.py`; it imports Flet and
  the standard library only, never another Afanes UI module.
- The architecture gate forbids new module-level functions outside a small allowlist, so the theme
  cannot be produced by a `build_theme()` helper. It must be expressed as module-level constants.
- Colors, spacing, and dimensions live in `theme.py`; views must not contain literal colors.
- `ThemeMode.SYSTEM` already provides the "follow the operating system" behavior from the spec;
  only the theme assignment is missing.
- Flet 1.1.2 separates `Page.theme` (light) from `Page.dark_theme` (dark). Both must be assigned
  to control each mode deliberately.

## Goals / Non-Goals

**Goals:**

- One explicit theme definition driving both modes, with no reliance on Flet defaults for the
  roles the interface uses.
- A familiar engineering-tool base: white surfaces separated by borders, one blue accent for
  selection and focus, and one green action color for filled primary buttons.
- A visible depth stack (page, structural region, card) built from boundaries plus a neutral
  selected-row fill, so it stays visible in both modes.
- Section identity in the sidebar that is redundant with label and icon, using familiar attention,
  success, and done hues.
- A hierarchy change confined to typography styles and tokens, with no new font dependency.

**Non-Goals:**

- An in-app theme switcher, theme persistence, or additional color schemes.
- Bundling or licensing a custom font.
- Restyling dialogs, changing control density, or reorganizing navigation.
- Changing any vault, parsing, or state behavior.

## Decisions

### Decision: assign one `ft.Theme` constant to both `page.theme` and `page.dark_theme`

`theme.py` exposes `THEME = ft.Theme(color_scheme_seed=THEME_SEED, surfaces=ft.ThemeSurfaces.TONAL)`,
and `_Shell._configure` assigns it to both slots. Flet derives the light ramp for `theme` and the
dark ramp for `dark_theme` from the same seed, so both modes share one definition and neither
depends on an implicit default.

Alternatives considered: assigning only `page.theme` and letting Flet default the dark side (fails
the spec's "every role resolves" requirement); hand-setting a full `ColorScheme` per mode (more
control, but ~40 roles to maintain and no evidence partial overrides merge predictably in Flet
1.1.2).

### Decision: engineering-tool blue seed with tonal surfaces

The seed is a familiar engineering-tool accent blue (`#0969DA`), and `ThemeSurfaces.TONAL` lets
Material tint the neutral ramp. That produces a near-white light canvas with a faint blue cast and
a blue-black dark canvas, close to the familiar `#F6F8FA` / `#0D1117` reference values without
hand-maintaining a full color scheme. Material generates the matching dark accent (a lighter blue,
like the familiar `#2F81F7`) from the same seed.

Alternatives considered: `NEUTRAL` surfaces with the blue seed (closer to pure gray but loses the
blue-black dark canvas and the surface depth); a fully custom neutral ramp or a hand-copied token
table (maximum fidelity, but requires overriding many roles and risks partial-override behavior).
The palette borrows a familiar reference, not a byte-for-byte copy.

### Decision: a three-token surface stack

The stack becomes explicit instead of one repeated token:

- `PAGE_SURFACE_COLOR` — the page canvas (`SURFACE_CONTAINER_LOWEST`, applied as `page.bgcolor`),
  so the background is white in light mode and near-black in dark mode.
- `REGION_SURFACE_COLOR` — structural regions such as the sidebar (`SURFACE_CONTAINER_LOWEST`),
  kept white and separated from the content by a 1 px boundary.
- `CARD_SURFACE_COLOR` — cards, panels, and the note canvas (`SURFACE_CONTAINER_LOWEST`), kept
  white so long-form Markdown is the brightest surface in light mode.
- `BORDER_COLOR` — `OUTLINE_VARIANT`, applied as a 1 px border on cards and regions.
- `SELECTED_ROW_COLOR` — `SURFACE_CONTAINER_HIGHEST`, the neutral fill for a selected list row.

`SURFACE_CONTAINER_COLOR` stays as an alias so existing views and tests keep working during the
migration; the new names describe intent. `STEP_SURFACE_COLOR` becomes
`SURFACE_CONTAINER_LOW` with normal text, so a step card reads as a quiet neutral panel instead of a
blue block.

Alternative considered: the earlier tinted three-step stack. Rendered next to the reference style it
read as a blue-gray wash; white surfaces plus a boundary match the familiar light theme more closely
and keep the Markdown canvas bright. Adding elevation shadows was also rejected: shadows are
unreliable across desktop/web renderers and disappear in dark mode.

### Decision: blue accent for state, green action color for primary buttons

The theme keeps `PRIMARY` (blue) for links, focus rings, the active-section edge, and selected-row
text, and sets the filled-button theme to a green action color with white text. The filled-button
theme also covers hover and pressed states, so every primary button stays consistent without
per-view styling. The two hues never trade places: green appears only on filled primary buttons,
blue only on selection, focus, and links. This follows the familiar light-tool convention while
keeping one meaning per hue.

Alternatives considered: blue filled buttons (the earlier iteration, which read heavier than the
reference style); green everywhere (would make focus and links read as "action").

### Decision: a compact status bar replaces the permanent header row

The vault path, refresh action, and vault menu move into a status bar at the bottom of the
workspace. The static app-name heading is removed: the native window title and the note title
already identify the context, and the freed row gives the Markdown canvas the vertical space it
needs on a 720 px window.

Alternative considered: keeping a top header and shrinking the vault text. The result still spends a
full row on static chrome and leaves the note canvas shorter, so the status bar wins.

### Decision: edit modes take the remaining page height

The page pane keeps one scrollable read column for rendered Markdown, and shows the label form and
body editor as its siblings. While a normal edit or raw rescue is active, the read column is hidden
so it no longer competes for the same expanded height; the editor column then expands, and so does
the body field inside it. The Markdown area therefore grows with the window instead of stopping at
`PAGE_BODY_MIN_LINES`.

Alternative considered: raising the fixed line count. It still leaves the pane half empty on a large
window and wastes space on a small one.

### Decision: a warm notice surface for due work

The launch digest uses a translucent attention tint (`NOTICE_SURFACE_COLOR` and
`NOTICE_BORDER_COLOR`) instead of the neutral card surface. The tint is derived from one amber
constant with opacity, so it darkens naturally in dark mode without a second palette. Its text keeps
the standard on-surface role, which preserves the contrast already verified for body text; only the
container is warm.

Alternative considered: setting amber text on an amber background to mirror a notice banner. The
translucent background makes that pairing mode-dependent and risks falling below 4.5:1, so the
neutral text is kept.

### Decision: section identity via four icon-color constants and an accent edge

`theme.py` defines `INBOX_SECTION_COLOR`, `PROJECTS_SECTION_COLOR`, `REFERENCES_SECTION_COLOR`, and
`REVIEW_SECTION_COLOR`. `views/workspace.py` builds the enum-to-color map next to its existing
`_SECTION_ICONS` map, so `theme.py` never imports `ui.state` and stays an import leaf. Values start
from familiar foreground hues: attention for Inbox, success for Projects, done for References, and
the accent for Review; Needs attention keeps the semantic error role.

Rules that keep the palette calm:

- Section colors apply only to the leading icon of a section tile.
- The active section is marked by the existing `selected` state plus a 3 px accent edge; the edge
  uses the single accent, not the section color.
- Section colors never color text, borders, buttons, or card backgrounds.

Alternatives considered: a `MappingProxyType` keyed by section string value in `theme.py` (works,
but stringly typed and easy to desynchronize); tinting section group headers and cards (adds a third
signal layer and turns the sidebar into a rainbow).

### Decision: hierarchy through theme text styles, not a font family

`theme.py` defines a small set of `ft.TextStyle` constants (page title, section label, metadata)
built on the platform font with explicit size and weight. Views continue to use
`ft.TextThemeStyle` for standard roles. No `font_family` is set on `ft.Theme`, so packaged builds
need no font files and Windows/macOS/Linux each render with their platform family.

Alternative considered: setting `Theme.font_family` to a bundled typeface. Rejected: it adds assets,
licensing, and build-size cost for a visual gain the spec does not require.

### Decision: contrast is verified per mode before the change is accepted

Because tonal surfaces and a blue accent shift every `on_*` pair, the task list includes a contrast
pass in both modes: body text 4.5:1, muted text and icons 3:1, focus indicators visible against
both the control and its container. If a generated pair fails, the fix is a named override constant
in `theme.py`, not a per-view color.

## Risks / Trade-offs

- **White-on-white surfaces could lose their separation** → the 1 px `OUTLINE_VARIANT` border carries
  the structure; check it in both modes and darken the border role or add a surface step only if the
  rendered boundary disappears.
- **Green action buttons and blue accents could blur together** → each hue has one job (green only on
  filled primary buttons, blue only on selection/focus/links), so the meaning stays learnable.
- **Flet may not merge a partial `ColorScheme` override predictably** → the design avoids partial
  overrides; if contrast needs a fix, verify the override renders in a running window before
  spreading it across views.
- **Existing tests hard-code token identities** (for example `STEP_SURFACE_COLOR` and
  `STEP_MUTED_ACTION_COLOR`) → keep token names stable and change values only; update assertions
  that encode surface identity rather than names.
- **Section tints could become a color-only signal** → the tint is confined to the icon, and the
  active edge plus selected state carry the actual state.
- **The dark palette is the flattest today** → treat dark mode as the first visual check in every
  task that touches surfaces, not as an afterthought.
- **The reference is a guide, not a contract** → do not hand-copy every reference token; keep the
  derived Material palette coherent and adjust only the seed and named overrides when contrast
  requires it.
- **`theme.py` growing into a grab bag** → keep it to tokens and styles only; no theme factory, no
  layout helpers, no view-specific logic.

## Migration Plan

The change is presentation-only, with no data migration and no persisted settings. Order of work:
theme constants and shell assignment first, then surfaces, then section identity, then typography,
then the contrast pass and the regenerated documentation screenshots. Each step is independently
revertible because views read named tokens rather than literal colors. Rolling back means reverting
the commits; no vault file, cache, or settings file is touched.
