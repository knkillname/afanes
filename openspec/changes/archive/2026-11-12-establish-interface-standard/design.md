# Design

## Context

See `proposal.md` for motivation and `specs/interface-theme/spec.md` for the requirements this
design satisfies. Current constraints that shape the approach:

- `src/afanes/ui/theme.py` is the single source of truth for color: no hex literal and no
  `ft.Colors.*` appears anywhere else under `src/afanes/ui/`. The remaining leak is numeric.
- `ui/` is 6,888 lines across 8 views and 11 components. A big-bang conversion is not reviewable.
- `page.theme` and `page.dark_theme` are assigned distinct `ft.Theme` objects in `ui/app.py`.
- Flet 1.1.2 is Flutter/Material underneath. `ft.Theme` exposes `color_scheme`, `surfaces`
  (`NEUTRAL`/`TONAL`), per-component themes, `visual_density`, and shape control through
  `ButtonStyle`. It does not expose GTK widgets or a high-contrast input.
- The reference is pinned to **libadwaita 1.8.0**. Its surface, accent, destructive, and
  typography tokens are the source of truth for the values below.
- The first wave 0 used the pre-1.8 neutrals (`#FAFAFA`, `#EBEBEB`, `#242424`, `#303030`,
  `#1E1E1E`), Material text-role names, and a 15% accent selection. A re-verification against the
  HIG and the libadwaita 1.8.0 stylesheet found those choices are not strict Adwaita. This
  revision corrects the foundation before the change is archived.

## Goals / Non-Goals

**Goals**

- Strict conformance to the GNOME Human Interface Guidelines, using Adwaita 1.8.0 as the
  reference implementation.
- A coherent, layered palette with independent light and dark definitions.
- A durable gate with a baseline that can only shrink, so every future view is bound to the
  standard while the existing tree migrates in waves.
- A reviewable wave 0: tokens, theme assignment, selection, action styling, icons, typography,
  minimum size, and the gate. No shell restructuring.
- Only the genuine Flet toolkit limits are declared. Discretionary deviations are removed.

**Non-Goals**

- Wave 1-7 work: shell composition and max content width, control-hierarchy sweep, writing-style
  pass, feedback and undo, keyboard and accessibility, adaptive breakpoints, placeholder pages,
  and the app icon.
- Bundling any font or icon asset.
- Replacing Flet's overlays with custom surfaces.
- Changing vault behavior, the CLI, or the note model.

## Decisions

### D1. Two explicit color schemes from a pinned reference

Define `LIGHT_THEME` and `DARK_THEME` as distinct `ft.Theme` objects, each with an explicit
`ft.ColorScheme`, and assign them to `page.theme` and `page.dark_theme`. The values come from
libadwaita 1.8.0, not from a seed and not from an earlier Adwaita generation.

*Why:* a seed lets Material derive every surface, which is how the page, sidebar, and card
collapsed onto one value. Explicit values are auditable in a test and match the reference
implementation's method.

*Alternative:* keep the seed and override only the broken roles. Rejected: derivation reintroduces
Material tonal values behind our back.

### D2. Neutral surfaces, not tonal

Set `surfaces=ft.ThemeSurfaces.NEUTRAL`.

*Why:* Material tonal surfaces tint every neutral with the seed. Adwaita's neutrals are neutral.
Leaving tonal on would mix an Adwaita palette with Material tinting and reproduce the muddy look.

### D3. Four surface roles from the reference tokens

| Role | Light | Dark | Reference token |
| --- | --- | --- | --- |
| Page / window | `#FAFAFB` | `#222226` | `--window-bg-color` |
| Region / sidebar | `#EBEBED` | `#2E2E32` | `--sidebar-bg-color` |
| Card / note view | `#FFFFFF` | `#1D1D20` | `--view-bg-color` |
| Container / panel | `#F3F3F5` | `#28282C` | `--secondary-sidebar-bg-color` |
| Header bar (wave 1) | `#FFFFFF` | `#2E2E32` | `--headerbar-bg-color` |

*Why:* four distinct values per mode fix the measured root cause. In light mode the note view is
the brightest surface. In dark mode the note view is darker than the window and sidebar, which is
the reference depth direction. The secondary-sidebar token supplies a solid neutral step for a
panel inside a view without depending on alpha compositing.

The reference `--card-bg-color` in dark mode is translucent white at 8%, and the note canvas is
the reading surface, so the canvas uses `--view-bg-color` and the in-view panel uses the secondary
sidebar token. This keeps every token solid and testable in Flet.

*Alternative:* use only borders for separation. Rejected: that is the current design and the
source of the complaint.

### D4. Accent fill and accent text are separate roles

| Role | Light | Dark | Use |
| --- | --- | --- | --- |
| `ACCENT_FILL` | `#3584E4` (Blue 3) | `#3584E4` | suggested fills, focus rings |
| `ACCENT_TEXT` | `#1C71D8` (Blue 4) | `#99C1F1` (Blue 1) | links and small accent labels on the view |
| `ON_ACCENT` | `#FFFFFF` | `#FFFFFF` | text on an accent or destructive fill |
| `DESTRUCTIVE` | `#E01B24` (Red 3) | `#C01C28` (Red 4) | destructive fills and labels |

Measured contrast: Blue 3 on white is about 3.77:1; it passes 3:1 for fills, focus, and boundaries
but not 4.5:1 for body text. Blue 4 on white is about 4.77:1. Blue 1 on the dark view is above
7:1. Red 3 with white is about 4.8:1; Red 4 with white is about 6.1:1. The split is what makes one
accent usable for both jobs without shipping unreadable links.

The suggested-action label inherits the reference's 3.77:1. The 4.5:1 rule applies to body,
muted, and accent text on neutral surfaces, not to a label sitting on the accent fill. That
inherited tension is documented rather than hidden.

*Alternative:* one accent value. Rejected: it fails the spec's own 4.5:1 text requirement.

### D5. Selection is the neutral navigation-sidebar treatment

`SELECTED_ROW_COLOR = ft.Colors.with_opacity(0.10, ft.Colors.ON_SURFACE)`, with no accent tint
and no accent edge. The selected row keeps the standard label and icon; the value step marks the
selection.

*Why:* libadwaita's `.navigation-sidebar` style explicitly makes selected items use a neutral color
instead of the accent. The previous 15% accent tint plus 3px accent edge was a deliberate deviation,
not Adwaita. The neutral fill is still a non-hue signal, so the state remains readable without
color perception.

*Alternative:* keep the accent tint because it is more visible. Rejected: it contradicts the
reference implementation and the maintainer's strict-adherence decision.

### D6. Suggested actions are accent; destructive actions get their own style

`filled_button_theme` uses `ACCENT_FILL`/`ON_ACCENT`. `DESTRUCTIVE_BUTTON_STYLE` uses `DESTRUCTIVE`
for actions that move or discard a note. The separate green `ACTION_COLOR` stays removed.

*Why:* one accent is the point of the standard. The current green was a second action hue borrowed
from a different design system. This decision changes which color suggestion uses; it does not yet
remove the extra suggested buttons. Wave 2 enforces one suggested-or-destructive action per view.

### D7. Radii and spacing follow the reference rhythm

- `SURFACE_RADIUS = 12` (`$card_radius`)
- `CONTROL_RADIUS = 9` (`$button_radius`)
- `ITEM_GAP = 12`, `SECTION_GAP = 18`, `PAGE_PADDING = 24`
- Button and input shapes are set through the themes so Material's stadium default does not survive.

*Why:* radius and rhythm do more for the flat impression than color, and Flet lets us set both
centrally. The control radius is corrected from 8 to the reference 9.

### D8. The gate is a test module, not a new tool

Add `tests/ui/test_conformance.py` with a rule table, an embedded baseline mapping
`rule -> {path: count}`, and two directions of failure: a count above baseline is a new violation; a
count below baseline is a stale entry that must be deleted in the same change.

*Why:* `AGENTS.md` 2.1 allows only Ruff, Pyrefly, pytest, and coverage; a custom linter script would
violate that. The test runs in `hatch test` and is visible in the same place as the existing
architecture gate.

*Detection:* color, numeric, font-size, and text-role rules use source scanning with a per-file
allowlist. Button rules use `ast` and count within the view class scope, not the whole module, so a
module that holds several dialogs is measured per view. Palette, surface, selection, and contrast
rules import `afanes.ui.theme` and compute values directly. The strict rules added here are: neutral
selection, reference surface tokens, GNOME text roles instead of Material `theme_style` names, icon
sizes from tokens, the 1024x600 minimum window, and one suggested-or-destructive action per view.

*Alternative:* hashed line allows. Rejected: every reformat invalidates the baseline.

### D9. Declared differences

The maintainer chose not to bundle assets: fewer moving parts to maintain. The differences are
therefore bounded to the four limits this implementation declares, and each names the limiting layer.

| Reference behavior | Afanes | Status | Why |
| --- | --- | --- | --- |
| Adwaita symbolic icon set | Material symbolic/outlined glyphs, tinted in code | permanent, asset-free | no bundled SVG set; consistency across platforms |
| libadwaita widget rendering | Flet/Material widget internals: field labels, ink feedback, scrollbars, overlay chrome | temporary, shrinking | Flet boundary; wave 0 sets feedback colors, radii, and density centrally |
| Access-key mnemonics | no underlined Alt shortcuts | permanent, Flet limit | Flet exposes no mnemonic API |
| High-contrast style | no separate high-contrast input | permanent, Flet limit | Flet exposes no high-contrast input; Flutter exposes one |

The platform typeface is **not** a difference: the typography guideline requires the system font.
The remaining obligation is to verify the resolved family on each platform. If Flutter resolves to
Roboto instead of the platform family, the application sets the platform family explicitly or the
platform variation is recorded separately.

These are *declared*, not accidental. Any document that claims conformance must list them, and the
spec bounds the list so a fifth difference cannot appear without a change.

Icon sizes use `ICON_SIZE = 16` for rows and `ICON_SIZE_LARGE = 32` for standalone or large
icons, matching the symbolic sizes. The current arbitrary `size=18` is removed.

### D10. Section identity becomes monochrome and neutral

The four per-section hues stay retired. Every section icon uses one neutral tint. The active
section uses the neutral selected-row fill, not an accent tint, accent icon, or accent edge. The
accent is reserved for suggested actions, focus, links, and log marks.

*Why:* strict adherence. The HIG palette cannot supply four section hues that also clear the
spec's 3:1 icon-contrast rule on the sidebar surface — Yellow 5 (`#E5A50A`) reaches only about
1.8:1 on `#EBEBED`, Green 5 (`#26A269`) about 2.7:1, Orange 4 (`#E66100`) about 2.9:1 — and
libadwaita avoids exactly this problem by making symbolic icons monochrome and navigation-sidebar
selection neutral.

*Alternative:* keep the four hues because they pass contrast. Rejected by the maintainer's decision
to prefer strict adherence over preserving the old identity.

### D11. The GNOME text scale replaces the Material vocabulary

Define the standard roles as relative percentages of an 11 pt-equivalent base
(`BASE_FONT_SIZE = 15`), and attach the values to both themes. The Flet `TextTheme` slots are an
implementation detail; the durable role names are the GNOME styles, exposed through a
`TEXT_ROLES` value object in `theme.py`. Views select a standard role rather than a Material
`theme_style` name.

| GNOME role | Base % | Size | Weight | Flet slot | Use |
| --- | --- | --- | --- | --- | --- |
| `title-1` | 181% | 27 | 800 | `headline_medium` | page title |
| `title-2` | 136% | 20 | 800 | `headline_small` | step headline, welcome |
| `title-3` | 136% | 20 | 700 | `title_large` | page and section headings |
| `title-4` | 118% | 18 | 700 | `title_medium` | panels and groups |
| `heading` | 100% | 15 | 700 | `title_small` | compact headings, control labels |
| `body` | 100% | 15 | 400 | `body_medium` | prose |
| `caption` | 82% | 12 | 400 | `body_small` | metadata and captions |
| `caption-heading` | 82% | 12 | 700 | `label_medium` | section captions |

The roles carry the text and muted colors from the tokens. The scale is computed from
`BASE_FONT_SIZE`, so changing the base scales every role proportionally, as the typography
guideline requires. The application does not bundle a font.

*Why:* the typography guideline says not to hard-code font styles or sizes and to use the standard
styles, or express sizes as relative values. The previous theme used Material role names and an
absolute scale that did not match the reference. This table is the reference scale in one place.

*Alternative:* keep the Material `theme_style` names and only change their sizes. Rejected: the
call sites would still speak Material, and the gate could not distinguish a standard role from a
toolkit slot.

*Note:* large-text robustness is separate. `PAGE_FORM_FIELD_HEIGHT` is fixed at 56, so label
clipping under large text is handled in the accessibility wave, not here.

## Risks / Trade-offs

- **Neutral selection is less prominent than the accent tint** -> verify at 1024x600 and 1100x760
  in both modes; the value step plus the label and icon must be visibly distinct.
- **The suggested fill label is 3.77:1** -> document it as inherited from Adwaita; do not claim
  4.5:1 for labels on the fill, and keep 4.5:1 for body, muted, and accent text on neutral
  surfaces.
- **The strict palette changes screenshots and tests again** -> accept the churn before 1.0; the
  change is explicitly a second visual pass.
- **Flutter may resolve a different font family than the platform** -> verify on Linux, macOS, and
  Windows; set the platform family explicitly if the resolved family is Roboto.
- **The dark reference card token is translucent** -> use the solid view token for the note canvas
  and the secondary-sidebar token for in-view panels; assert the composited result in tests.
- **The baseline becomes a permanent excuse** -> the gate fails on stale entries, so every
  migration must shrink it, and the roadmap names the waves.
- **Per-view counting is more complex than per-module counting** -> count within the view class
  scope; keep a module-level fallback only for a module that holds one view.
- **Strict adherence is staged, so the app is visibly non-conformant between waves** -> the
  standard document lists the open gaps and their waves, and the baseline must shrink with every
  migration; the four Flet limits are the only permanent exceptions.
- **Losing the section hues weakens at-a-glance scanning** -> the active row's neutral fill plus
  the label and icon carry identity; verify that Inbox, Projects, and References remain easy to
  tell apart.
- **A future change adds a fifth difference silently** -> the spec bounds the list and requires a
  change to extend it; the docs page and the spec must agree.

## Migration Plan

Wave 0 lands in this change. Later waves are separate changes and get their own spec deltas.

```text
WAVE 0  this change     strict libadwaita 1.8.0 tokens, neutral selection,
                        GNOME standard type scale, symbolic/outlined icons,
                        1024x600 minimum window, expanded gate
WAVE 1  next            shell composition: header bar and chrome frame,
                        sidebar as chrome, max content width, panel/radius/
                        spacing sweep
WAVE 2  later           control hierarchy: one suggested or destructive action
                        per view, icon XOR label, dense rows, insensitive
                        invalid actions instead of error-on-click
WAVE 3  later           writing style: header capitalization, ellipses, final
                        periods, neutral tone (avoid you/my), typographic
                        apostrophes and ellipsis, copy gate, AGENTS.md 4.6
WAVE 4  later           feedback: undo over confirmation, toasts for one-time
                        events, banners only for persistent states, overlays
WAVE 5  later           keyboard and accessibility: shortcut map, focus order,
                        semantics labels, large-text robustness
WAVE 6  later           adaptivity: breakpoints, collapsible sidebar, narrow
                        and large-window behavior
WAVE 7  later           identity: app icon, placeholder pages, final palette
                        pass, empty baseline
```

Waves are ordering, not exemptions. The target is strict HIG conformance; the baseline is a debt
ledger that must reach empty at wave 7, and no wave may add an entry to it.

Rollback: wave 0 is one commit series over `theme.py`, `app.py`, the selection, action, icon,
section, and typography styles, the gate, and the tests that assert them. Reverting restores the
previous tokens; no vault, CLI, or data-model change is involved.

## Verification notes

Re-verified against the GNOME HIG index and the linked pages for UI styling, typography, UI icons,
writing style, accessibility, keyboard, adaptivity, buttons, sidebars, header bars, selection, and
placeholder pages, plus the libadwaita 1.8.0 stylesheet.

The audit corrected these previous claims:

- the palette used pre-1.8 Adwaita neutrals rather than the current window, sidebar, view, and
  secondary-container tokens;
- the text theme used Material role names and an absolute scale rather than the GNOME standard
  styles;
- selection used an accent tint and edge rather than the neutral navigation-sidebar treatment;
- the light destructive fill used Red 4 rather than Red 3;
- the high-contrast and mnemonic limits were attributed to Flutter rather than Flet.

The previous verification pass was made against the old bounded assumptions and is superseded by
this audit.

Observed and deliberately deferred to later waves:

- several filled actions per screen remain; wave 2 enforces one suggested-or-destructive action.
- dialog-opening labels do not yet use ellipses, many strings end in periods, three strings use
  “you” or “your”, and two use straight apostrophes; wave 3 fixes the copy and adds a copy gate.
- invalid forms show an error after the click instead of disabling the action; wave 2 changes the
  control behavior.
- one-time status messages still use the banner component; wave 4 separates toasts from banners.
- accessible names are sparse and there are no application shortcuts; wave 5 covers semantics and
  keyboard.
- there is no maximum content width; wave 1 adds the content frame and wave 6 completes the
  adaptive behavior. The minimum window is now 960x600, so a 1024x600 desktop is supported.
- the browser and page empty states are one-line messages rather than placeholder pages; wave 7
  adds headings, descriptions, and the app icon.
- the template dropdown's floating label overlaps its outline. This is the declared Flet
  widget-rendering difference; wave 1 revisits overlay and field chrome.

Reviewed the strict build at 1024x600 and 1100x760 in light and dark mode. The sidebar search stays
visible after `LIST_TILE_THEME.min_height = 36`; the browser list scrolls in its remaining viewport.
At 1024x600 the page title wraps to two lines because the header action row is wide; wave 1 shell
composition and wave 2 control hierarchy address it. No control clips horizontally.

Font resolution: the theme leaves `font_family` unset, so Flutter uses the platform font. On this
Linux host `fc-match sans-serif` resolves Noto Sans; Adwaita Sans is installed, but Flutter selects
the fontconfig default. macOS and Windows use their system UI fonts. No font asset is bundled; the
per-platform visual check remains in the release checklist.

Permanent Flet limits: the Material icon set is the asset-free icon difference; widget internals
remain toolkit-rendered; access-key mnemonics and high-contrast input are unavailable.

## Open Questions

None. The open decisions are settled: section identity is monochrome with neutral selection, no
font or icon assets are bundled, typography uses the GNOME standard scale, and only the four Flet
limits are permanent differences.
