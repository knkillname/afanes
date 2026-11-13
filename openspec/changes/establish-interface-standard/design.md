# Design

## Context

See `proposal.md` for motivation and `specs/interface-theme/spec.md` for the requirements this
design satisfies. Current constraints that shape the approach:

- `src/afanes/ui/theme.py` is already the single source of truth for color: no hex literal and no
  `ft.Colors.*` appears anywhere else under `src/afanes/ui/`. The leak is numeric — 76 layout
  literals across 11 files (18 in `components/calendar.py`, 13 in `views/workspace.py`).
- `ui/` is 6,888 lines across 8 views and 11 components. A big-bang conversion is not reviewable.
- `page.theme` and `page.dark_theme` are assigned the same `THEME` object in `ui/app.py`.
- Flet 1.1.2 is Flutter/Material underneath. `ft.Theme` exposes both `color_scheme_seed` and a full
  `color_scheme`, `surfaces` (`NEUTRAL`/`TONAL`), per-component themes, `visual_density`, and shape
  control through `ButtonStyle`. It does not expose GTK widgets.
- The package is at 0.6.0, so a visible identity break is cheap now and expensive after 1.0.

## Goals / Non-Goals

**Goals**

- Give the interface a coherent, layered palette with independent light and dark definitions.
- Make the standard durable: a build-time gate with a baseline that can only shrink, so every future
  view is bound to the standard while the existing tree migrates in waves.
- Keep the change reviewable: wave 0 touches tokens, theme assignment, selection, action styling,
  section icons, and the gate. No layout restructuring.
- Treat strict conformance as the target: every wave reduces the gap, and the baseline reaches empty
  at the end of the plan.

**Non-Goals**

- Wave 1-7 work: shell composition, control-hierarchy sweep, writing-style pass, undo and feedback,
  keyboard and accessibility, adaptive breakpoints, custom app icon.
- Bundling any font or icon asset. Both are permanent declared differences, recorded below.
- Replacing Flet's overlays with custom surfaces.
- Changing vault behavior, the CLI, or the note model.

## Decisions

### D1. Two explicit color schemes instead of one seed

Define `LIGHT_THEME` and `DARK_THEME` as distinct `ft.Theme` objects, each with an explicit
`ft.ColorScheme`, and assign them to `page.theme` and `page.dark_theme`.

*Why:* a seed lets Material derive every surface, which is exactly how the page, sidebar, and card
collapsed onto one value and how the "dark" palette became light values with a derived tint. Explicit
values are auditable in a test and match Adwaita's method (a palette, not an algorithm).

*Alternative:* keep the seed and override only the broken roles. Rejected: derivation would keep
reintroducing M3 tonal values behind our back.

### D2. Neutral surfaces, not tonal

Set `surfaces=ft.ThemeSurfaces.NEUTRAL`.

*Why:* M3 tonal surfaces tint every neutral with the seed. Adwaita's neutrals are neutral. Leaving
tonal on would mix an Adwaita palette with Material tinting and reproduce the current muddy look.

### D3. Three surface roles, with the depth direction flipping in dark mode

| Role | Light | Dark | Meaning |
| --- | --- | --- | --- |
| `PAGE_SURFACE_COLOR` | `#FAFAFA` | `#242424` | window |
| `REGION_SURFACE_COLOR` | `#EBEBEB` | `#303030` | sidebar, chrome |
| `CARD_SURFACE_COLOR` | `#FFFFFF` | `#1E1E1E` | note canvas |
| `SURFACE_CONTAINER_COLOR` | `#F6F5F4` | `#303030` | panel inside a card |

*Why:* three distinct values per mode fix the measured root cause. In light mode content is brightest
(the existing requirement); in dark mode the canvas is darker than chrome, which is Adwaita's actual
behavior and the reason a dark theme cannot be "light theme inverted".

*Alternative:* use only borders for separation. Rejected: that is the current design and the source
of the complaint.

### D4. Accent fill and accent text are separate roles

| Role | Light | Dark | Use |
| --- | --- | --- | --- |
| `ACCENT_FILL` | `#3584E4` (Blue 3) | `#3584E4` | suggested fills, focus rings, selection tint |
| `ACCENT_TEXT` | `#1C71D8` (Blue 4) | `#99C1F1` (Blue 1) | links, small accent labels |
| `ON_ACCENT` | `#FFFFFF` | `#FFFFFF` | text on an accent fill |
| `DESTRUCTIVE` | `#C01C28` (Red 4) | `#C01C28` | destructive fills and labels |

Measured contrast: Blue 3 on white ~3.8:1 (passes 3:1 for fills, focus, and boundaries, fails 4.5:1
for text); Blue 4 on white ~4.8:1; Blue 1 on `#242424` ~7.9:1. The split is what makes one accent
usable for both jobs without shipping unreadable links.

*Alternative:* one accent value. Rejected: it fails the spec's own 4.5:1 text requirement.

### D5. Selection is an accent tint plus the existing edge marker

`SELECTED_ROW_COLOR = ft.Colors.with_opacity(0.15, ACCENT_FILL)`, keeping the 3px accent edge on the
active section. Selection text stays `ON_SURFACE`.

*Why:* Adwaita marks selection with a low-opacity accent pill. The edge marker keeps the state
readable without hue, which the spec requires.

### D6. Suggested actions are accent; destructive actions get their own style

`filled_button_theme` uses `ACCENT_FILL`/`ON_ACCENT`. A new `DESTRUCTIVE_BUTTON_STYLE` uses
`DESTRUCTIVE` for actions that move or discard a note. The separate green `ACTION_COLOR` is removed.

*Why:* one accent is the point of the standard. The current green is a second action hue borrowed from
a different design system, and it is what makes "Start review", "Capture", and "Edit" all shout at
once. This decision changes *which* color suggestion uses; it does not yet remove the extra suggested
buttons (wave 2).

### D7. Radii and spacing move to an Adwaita-like rhythm

- `SURFACE_RADIUS = 12` (replaces `CARD_RADIUS = 6`)
- `CONTROL_RADIUS = 8` (button and field corner radius)
- `ITEM_GAP = 12`, `SECTION_GAP = 18`, `PAGE_PADDING = 24` (from 8/16/24)
- Button shape set through the button themes so Material's stadium/20px default does not survive.

*Why:* radius and rhythm do more for the "flat" impression than color, and Flet lets us set both
centrally.

### D8. The gate is a test module, not a new tool

Add `tests/ui/test_conformance.py` with a rule table, an embedded baseline mapping
`rule -> {path: count}`, and two directions of failure: a count above baseline is a new violation; a
count below baseline is a stale entry that must be deleted in the same change.

*Why:* `AGENTS.md` 2.1 allows only Ruff, Pyrefly, pytest, and coverage; a custom linter script would
violate that. The test runs in `hatch test` and is visible in the same place as the existing
architecture gate.

*Detection:* color and numeric rules use source scanning with a per-file allowlist. Button rules use
`ast` (count `ft.FilledButton` calls per module, and detect a call carrying both `icon` and
`content`/`text`/`label`). Palette and contrast rules import `afanes.ui.theme` and compute WCAG
ratios directly, which also converts the original flatness bug into a regression test.

*Alternative:* hashed line allows. Rejected: every reformat invalidates the baseline.

### D9. Declared differences

The maintainer chose not to bundle assets: fewer moving parts to maintain. The differences are
therefore bounded rather than open-ended, and each is labelled as either a guideline-preferred
choice or a toolkit limit.

| Reference behavior | Afanes | Status | Why |
| --- | --- | --- | --- |
| Adwaita Sans | platform typeface | permanent, guideline-preferred | the typography guideline asks for the system font; the family differs from GNOME's default |
| Adwaita symbolic icons | toolkit's monochrome interface icon set, tinted in code | permanent, asset-free | no bundled icon set; consistency across platforms |
| libadwaita widget rendering | toolkit internals: field label behavior, ink feedback, scrollbars, overlay chrome | temporary, shrinking | toolkit boundary; wave 0 removes the loudest seams |
| Access-key mnemonics | no underlined Alt shortcuts | permanent, toolkit limit | Flutter exposes no mnemonic mechanism |
| High-contrast style | no separate high-contrast palette | permanent, toolkit limit | Flutter exposes no high-contrast theme hook |

These are *declared*, not accidental. Any document that claims conformance must list them, and the
spec bounds the list so a sixth difference cannot appear without a change.

Wave 0 reduces the widget-rendering seam where Flet exposes the knob: control feedback colors come
from the accent and surface roles instead of Material defaults, and inputs take `CONTROL_RADIUS`.
Text-field label behavior and scrollbars remain toolkit-rendered until wave 1.

### D10. Section identity becomes monochrome

The four per-section hues are retired. Every section icon uses one neutral tint, and the active
section takes the accent in its icon, edge, and row tint. `LOG_ENTRY_TINT` and
`LOG_ENTRY_DOT_COLOR` become accent-derived; `REVIEW_SECTION_COLOR` collapses into the accent.

*Why:* strict adherence. The HIG palette cannot supply four section hues that also clear the spec's
3:1 icon-contrast rule on the region surface — Yellow 5 (`#E5A50A`) reaches only ~1.8:1 on `#EBEBEB`,
Green 5 (`#26A269`) ~2.7:1, Orange 4 (`#E66100`) ~2.9:1 — and Adwaita avoids exactly this problem by
making symbolic icons monochrome. The previous requirement mandated the hues; this change removes it
and replaces it with a monochrome treatment, which is the one place where the new standard overrides
existing spec text.

*Alternative:* keep the four hues because they pass contrast. Rejected by the maintainer's decision to
prefer strict adherence over preserving the old identity.

### D11. A single text theme replaces per-control type styles

Define `TEXT_THEME = ft.TextTheme(...)` and attach it to both palettes. Views select a role with
`theme_style=`; the four `*_TEXT_STYLE` constants and the inline style in `views/projects.py` are
removed.

| Role | Size / weight | Replaces | Used by |
| --- | --- | --- | --- |
| `HEADLINE_MEDIUM` | 28 / 700 | `PAGE_TITLE_TEXT_STYLE` | note title |
| `HEADLINE_SMALL` | 24 / 700 | `STEP_HEADLINE_TEXT_STYLE` | step headline, welcome, processing |
| `TITLE_LARGE` | 22 / 600 | existing call sites | page headings |
| `TITLE_MEDIUM` | 16 / 600 | existing call sites | panels, groups |
| `TITLE_SMALL` | 15 / 600 | existing call sites | compact headings |
| `BODY_MEDIUM` | 14 / 400 | default body | prose |
| `BODY_SMALL` | 12 / 400 | `METADATA_TEXT_STYLE`, inline projects style | metadata, captions |
| `LABEL_LARGE` | 14 / 600 | existing call sites | control labels |
| `LABEL_MEDIUM` | 12 / 700 | `SECTION_LABEL_TEXT_STYLE` | section captions |
| `LABEL_SMALL` | 11 / 500 | — | dense labels |

The theme defines all fifteen roles; the table lists the ones the application uses. Caption roles carry
`MUTED_TEXT_COLOR`; title and body roles carry `TEXT_COLOR`.

*Why:* the typography guideline says not to hard-code font styles or sizes and to use the standard
styles instead. Five sites hard-code a size today. One text theme is less code than four constants plus
an inline style, and it gives the conformance gate one rule to enforce.

*Alternative:* keep the four constants and centralize only their sizes. Rejected: per-control overrides
survive and cannot be gated.

*Note:* large-text robustness is separate. `PAGE_FORM_FIELD_HEIGHT` is fixed at 56, so label clipping
under large text is handled in the accessibility wave, not here.

## Risks / Trade-offs

- **Flutter overrides explicit values** (some widgets ignore `color_scheme` roles) -> assert resolved
  theme values and contrast in tests, then do one manual pass at 960x640 and 1100x760 in both modes.
- **Raised spacing overflows at the minimum window size** -> verify the sidebar at 960px; reduce
  `SECTION_GAP` or `SIDEBAR_WIDTH` if a row clips.
- **The baseline becomes a permanent excuse** -> the gate fails on stale entries, so every migration
  must shrink it, and the roadmap below names the waves.
- **Per-module counting is a proxy for per-view** -> document the approximation in the gate; view
  modules hold one view class each, so the proxy is faithful today.
- **Screenshots and prose become stale** -> regenerate the four screenshots and update any guide text
  that names the old colors or the neutral selection.
- **Neutral surfaces read as muddy in dark mode** -> the three values are separated by measurable
  steps (24/30/1E), and the test asserts distinctness; adjust during the manual pass if needed.
- **The text-theme roles do not reproduce Adwaita's scale exactly** -> the roles keep the current
  rendered sizes where they exist (28, 24, 12) and change only the weight and centralization; compare
  the four screenshots before and after.
- **A future change adds a sixth difference silently** -> the spec bounds the list and requires a
  change to extend it; the docs page and the spec must agree.
- **Strict adherence is staged, so the app is visibly non-conformant between waves** -> the standard
  document names the open waves, and the baseline must shrink with every migration; large text and
  access keys remain declared gaps until wave 5.
- **Strict adherence conflicts with previously accepted spec text** -> resolve the conflict in the
  delta instead of leaving both requirements standing; this change removes the section-tint
  requirement and rewrites the selection scenario rather than keeping a dormant contradiction.
- **Losing the section hues weakens at-a-glance scanning** -> the active section keeps an accent
  edge, icon color, and row tint, and the spec still requires the label and icon to identify the
  section without color; verify in the manual pass that Inbox, Projects, and References remain easy
  to tell apart.

## Migration Plan

Wave 0 lands in this change. Later waves are separate changes and get their own spec deltas.

```text
WAVE 0  this change     tokens, two palettes, three surfaces, accent roles,
                        selection tint, action styles, monochrome sections,
                        text theme, conformance gate
WAVE 1  next            shell composition: chrome frame, sidebar as chrome,
                        panel/radius/spacing sweep across views
WAVE 2  later           control hierarchy: one suggested action per view,
                        icon XOR label, row density
WAVE 3  later           writing style: header capitalization, ellipses,
                        final periods, pronouns, typographic apostrophes,
                        AGENTS.md 4.6 amendment
WAVE 4  later           feedback: undo over confirmation, overlay policy
WAVE 5  later           keyboard and accessibility: shortcut map, focus order,
                        semantics labels, large-text robustness
WAVE 6  later           adaptivity: breakpoints, collapsible sidebar
WAVE 7  later           identity: app icon, final palette pass, empty baseline
```

Waves are ordering, not exemptions. The target is strict conformance; the baseline is a debt ledger
that must reach empty at wave 7, and no wave may add an entry to it.

Rollback: wave 0 is one commit series over `theme.py`, `app.py`, the selection, action, and section
styles, the new gate, and the tests that assert them. Reverting restores the previous tokens; no
vault, CLI, or data-model change is involved.

## Verification notes

Reviewed on the packaged desktop client at 1100x760 and 960x640, in light and dark mode, with the
demo vault used for the documentation screenshots.

Observed as specified:

- the page, region, and card surfaces are distinct in both modes, and the note canvas is the brightest
  surface in light mode;
- dark mode flips the depth direction: the card is darker than the page, and the chrome is lighter;
- inactive section icons share the muted tint, while the active section takes the accent in its icon,
  the 3px edge, and the row tint;
- selection reads as a light accent tint plus the edge; the suggested style is the accent, not the
  retired green;
- the trash confirmation and the header trash action use the destructive style;
- the text hierarchy is visible: page title above body text, metadata in the muted role.

Observed and recorded rather than fixed here:

- at 960x640 the page-title column broke a word when the sidebar was 320 wide; `SIDEBAR_WIDTH` is now
  260, so the title wraps at a word boundary. No other row clipped after the change.
- one screen still shows several filled actions (the launch digest, Capture, Edit, and Move to Trash),
  and the review entry card adds its own. The conformance baseline records the filled-button count;
  wave 2 reduces each view to one suggested action.
- the template dropdown's floating label overlaps its outline. This is the declared toolkit
  widget-rendering difference; wave 1 revisits overlay and field chrome.
- access-key mnemonics and a high-contrast style remain permanent declared differences. Large-text
  robustness is still open and belongs to wave 5.

## Open Questions

None. The open decisions are settled: section identity is monochrome, no font or icon assets are
bundled, typography moves to the text theme, and access-key mnemonics plus high contrast are declared
toolkit limits.
