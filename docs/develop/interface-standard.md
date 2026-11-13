# 🎛️ Interface standard

Afanes follows the GNOME interface guidelines as its reference design language. The guidelines assume
GTK and libadwaita; Afanes runs on Flet and Flutter, so conformance means a bounded version of that
language: the palette, depth, typography, and icon rules are ours, while toolkit internals and two
unavailable mechanisms are declared differences. This page is the durable reference for that standard.

:::{admonition} tl;dr
:class: note

Every interface value comes from `src/afanes/ui/theme.py`. A test gate fails when a view hardcodes a
color, a layout number, an extra filled button, an icon-plus-label button, or a dense row. Existing
exceptions live in a baseline that may only shrink.
:::

## 🪜 Conformance levels

The standard has five levels, in the order a reviewer should check them:

1. **Palette and contrast.** Light and dark each define an independent palette. Body text, muted text,
   and accent text meet 4.5:1 against their surface; accent fills, icons, and control boundaries meet
   3:1.
2. **Surfaces.** The page, structural regions such as the sidebar, and content cards resolve to three
   distinct values in each mode. In light mode the note canvas is the brightest surface; in dark mode it
   is darker than the chrome, matching how depth flips.
3. **Accent, actions, and selection.** One accent supplies the suggested-action fill, selection tint,
   focus indicator, and active-section mark. Accent text is a separate, contrast-checked role.
   Destructive actions use a destructive style.
4. **Typography.** One platform font family and one text theme. Views select a named role
   (`HEADLINE_MEDIUM`, `BODY_SMALL`, `LABEL_MEDIUM`, and so on) instead of setting a size or weight.
5. **Control values and the ratchet.** Every color, radius, spacing value, and dimension comes from the
   token module, and the conformance gate keeps it that way.

## 🎨 Palette roles

| Role | Light | Dark | Use |
| --- | --- | --- | --- |
| Page surface | `#FAFAFA` | `#242424` | Window background |
| Region surface | `#EBEBEB` | `#303030` | Sidebar and chrome |
| Card surface | `#FFFFFF` | `#1E1E1E` | Note canvas and cards |
| Container surface | `#F6F5F4` | `#303030` | Panel inside a card |
| Accent fill | `#3584E4` | `#3584E4` | Suggested actions, focus, selection tint |
| Accent text | `#1C71D8` | `#99C1F1` | Links and small accent labels |
| Destructive | `#C01C28` | `#C01C28` | Actions that move or discard a note |

The accent exposes a fill role and a text role because the fill fails the 4.5:1 text threshold on light
surfaces. Selection is a 15% accent tint plus the 3px active edge; the tint is never the only signal.
Log marks use the accent. Unreadable notes and errors use the status error role, which is red in light
mode and a lighter red in dark mode so it stays readable.

## 🌓 Surfaces and depth

Light mode raises content: the card is brighter than the page, and the page is brighter than the
sidebar. Dark mode does the opposite, as Adwaita does: the card is darker than the page and the chrome
is lighter, so a panel reads as recessed rather than raised. Separation may combine a value step with
the 1px outline; the value step alone must be visible.

## 🏷️ Monochrome sections

The browser does not assign a color to each section. Every section icon uses the muted text tint, and
the active section takes the accent in its icon, its edge, and its row tint. The label and the icon
identify the section when color is not perceived. This retires the earlier per-section hue treatment,
which could not clear the 3:1 icon-contrast rule across the palette.

## 🔤 Text theme

`theme.TEXT_THEME` defines all fifteen standard roles. The ones in use:

| Role | Size / weight | Use |
| --- | --- | --- |
| `HEADLINE_MEDIUM` | 28 / 700 | Page title |
| `HEADLINE_SMALL` | 24 / 700 | Step headline and welcome |
| `TITLE_LARGE` | 22 / 600 | Page headings |
| `TITLE_MEDIUM` | 16 / 600 | Panels and groups |
| `TITLE_SMALL` | 15 / 600 | Compact headings |
| `BODY_MEDIUM` | 14 / 400 | Prose |
| `BODY_SMALL` | 12 / 400 | Metadata and captions, muted |
| `LABEL_LARGE` | 14 / 600 | Control labels |
| `LABEL_MEDIUM` | 12 / 700 | Section captions, muted |
| `LABEL_SMALL` | 11 / 500 | Dense labels, muted |

Views use `theme_style=ft.TextThemeStyle.<role>`. Markdown surfaces that cannot take a theme role pass
the style object that backs the role from the same text theme. A view does not set its own font size;
the conformance gate rejects `ft.Text(size=...)` outside the theme.

## 🔀 Bounded differences

The standard is strict, but it cannot be identical to GNOME's own implementation. These differences are
declared, not accidental; adding another one requires a change that updates this table and the
`interface-theme` spec.

| Reference behavior | Afanes | Status | Why |
| --- | --- | --- | --- |
| Adwaita Sans | Platform typeface | Permanent, guideline-preferred | The typography guideline asks for the system font; the family differs from GNOME's packaged default |
| Adwaita symbolic icons | Toolkit monochrome icon set, tinted in code | Permanent, asset-free | No bundled icon set; parity across platforms |
| libadwaita widget rendering | Toolkit internals: field labels, ink feedback, scrollbars, overlay chrome | Temporary, shrinking | Toolkit boundary; the theme now sets feedback colors, radii, and density |
| Access-key mnemonics | No underlined Alt shortcuts | Permanent, toolkit limit | Flutter exposes no mnemonic mechanism |
| High-contrast style | No separate high-contrast palette | Permanent, toolkit limit | Flutter exposes no high-contrast theme hook |

Screen-reader coverage is not a declared difference: Flet exposes semantics labels, so missing labels
are a gap to fix rather than a toolkit limit.

## 🚦 The conformance gate

`tests/ui/test_conformance.py` scans `src/afanes/ui` and compares six measurements with an embedded
baseline:

- color literals and `ft.Colors.*` outside the token module;
- numeric layout literals outside the token module;
- `ft.FilledButton` calls per module;
- controls carrying both an icon and a label;
- `dense=True` rows;
- hardcoded `ft.Text(size=...)`, `ft.TextStyle(size=...)`, or `font_size` outside the token module.

The comparison fails in both directions. A count above its baseline entry is a new violation; a
baseline entry above the measured count is stale and must be deleted in the same change. The baseline
is a debt ledger: it starts at the values measured when the gate landed and must reach empty before the
standard is considered complete. Never add an entry to make a change pass.

## 🧭 Migration waves

Wave 0 landed with the change that introduced this standard. Later waves are separate changes with
their own spec deltas:

```text
WAVE 0  tokens, two palettes, surfaces, accent roles, selection tint,
        action styles, monochrome sections, text theme, gate
WAVE 1  shell composition: chrome frame, sidebar as chrome, spacing sweep
WAVE 2  control hierarchy: one suggested action per view, icon XOR label,
        row density
WAVE 3  writing style: header capitalization, ellipses, final periods,
        second person, typographic apostrophes
WAVE 4  feedback: undo over confirmation, overlay policy
WAVE 5  keyboard and accessibility: shortcut map, focus order, semantics
        labels, large-text robustness
WAVE 6  adaptivity: breakpoints, collapsible sidebar
WAVE 7  identity: app icon, final palette pass, empty baseline
```

Waves are ordering, not exemptions. The target remains strict conformance.

## ✅ Changing the standard

A visual change gets its own OpenSpec change. It must say which level it touches, whether it adds a
difference, and how the gate and baseline move. If the change removes a baseline entry by migrating
the offending code, it deletes that entry in the same commit.
