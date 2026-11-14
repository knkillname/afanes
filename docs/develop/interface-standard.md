# 🎛️ Interface standard

Afanes follows the GNOME Human Interface Guidelines strictly, using libadwaita 1.8.0 as the
reference implementation. The guidelines assume GTK and libadwaita; Afanes runs on Flet and
Flutter, so five toolkit limits are declared rather than treated as design choices. Everything
else — palette, depth, selection, typography, icon treatment, and layout — follows the reference.

:::{admonition} tl;dr
:class: note

Every interface value comes from `src/afanes/ui/theme.py`. A test gate fails when a view hardcodes a
color, a layout number, a font size, a Material text role, a filled icon, or an extra suggested or
destructive action. Existing exceptions live in a baseline that may only shrink. A second gate checks
the writing style in the interface and command-line copy catalogs, with no baseline.
:::

## 🪜 Conformance levels

The standard has seven levels, in the order a reviewer should check them:

1. **Palette and contrast.** Light and dark each define the Adwaita 1.8.0 tokens independently.
   Body and muted text meet 4.5:1 on every neutral surface; accent text meets 4.5:1 on the note
   view; accent fills, icons, and control boundaries meet 3:1.
2. **Surfaces and depth.** The window, sidebar, note view, and secondary container resolve to four
   distinct values in each mode. Light raises the note view; dark recesses it below the window and
   sidebar, as the reference does.
3. **Accent, actions, and selection.** One accent supplies suggested actions, focus, and links.
   Selection uses the neutral navigation-sidebar row, not the accent. Destructive actions use the
   reference destructive fill. The active section keeps a non-hue cue.
4. **Typography.** One platform font family and the GNOME standard styles — `title-1` through
   `title-4`, `heading`, `body`, `caption`, and `caption-heading` — expressed as relative
   percentages of one base size.
5. **Control values and the ratchet.** Every color, radius, spacing, dimension, icon size, column
   width, content width, and minimum-window value comes from the token module, and the conformance
   gate keeps it that way.
6. **Writing style.** Headings and short control labels use header capitalization; field labels and
   prose use sentence capitalization; copy ends without a period; ellipses mark only actions that
   need further input; tone stays neutral; apostrophes and ellipses are typographic.
7. **Feedback.** The feedback surface follows the lifetime of the event: a toast for a one-time
   result or undo, an owned banner for a condition that remains true, inline text for a field or form
   problem, and a panel or dialog for a decision. Trash is immediate and offers Undo. A confirmed
   restore over an occupied birthplace and every permanent-delete action use an irreversible
   confirmation; the scheduled 30-day retention pass is silent because no user action invokes it.

## 🎨 Palette roles

| Role | Light | Dark | Reference token | Use |
| --- | --- | --- | --- | --- |
| Window | `#FAFAFB` | `#222226` | `--window-bg-color` | Window background |
| Sidebar | `#EBEBED` | `#2E2E32` | `--sidebar-bg-color` | Navigation region and chrome |
| Note view | `#FFFFFF` | `#1D1D20` | `--view-bg-color` | Markdown canvas and content cards |
| Secondary container | `#F3F3F5` | `#28282C` | `--secondary-sidebar-bg-color` | Panel inside a view |
| Body text | `#333334` | `#FFFFFF` | `--window-fg-color` | Prose and control labels |
| Muted text | `#5E5C64` | `#C0BFBC` | contrast-checked neutral | Metadata and captions |
| Accent fill | `#3584E4` | `#3584E4` | `--accent-bg-color` | Suggested actions, focus |
| Accent text | `#1C71D8` | `#99C1F1` | `--accent-color` | Links and small accent labels |
| On accent | `#FFFFFF` | `#FFFFFF` | `--accent-fg-color` | Text on an accent or destructive fill |
| Destructive | `#E01B24` (Red 3) | `#C01C28` (Red 4) | `--destructive-bg-color` | Actions that move or discard a note |
| Error text | `#4A0008` | `#FFD9D4` | `--error-fg-color` | Inline errors and banner text |

The muted text role uses a contrast-checked neutral instead of the reference's dim opacity, because
the dimmed token does not clear 4.5:1 for small text. Error text uses the error-container foreground
so it stays readable on both the note view and the error banner.

## 🌓 Surfaces and depth

Light mode raises content: the note view is brighter than the window, and the window is brighter
than the sidebar. Dark mode does the opposite: the note view is darker than the window, and the
sidebar is lighter than the window. The secondary container is a neutral step between the view and
the window for panels inside a view. Separation may combine a value step with the 1px outline; the
value step alone must be visible.

The note canvas uses `--view-bg-color`, not the reference's translucent dark card token, so the
reading surface stays a solid, testable value. The in-view panel uses the secondary-sidebar token
for the same reason. The navigation uses the sidebar surface, the browser uses the window surface,
and the detail uses the note-view surface, so the four reference roles stay unchanged.

## 📐 Window and columns

The window starts at 1100x760 and cannot shrink below 1024x600, the desktop floor in the reference
guidelines. The workspace divides the window into three regions that fill it, with minimum widths
protecting each resizable column:

| Token | Value | Use |
| --- | --- | --- |
| `NAVIGATION_WIDTH` | 240 | Destinations, counts, vault identity, primary menu |
| `DRAWER_WIDTH` | 280 | Transient navigation drawer at medium widths |
| `BROWSER_MIN_WIDTH` | 320 | Smallest usable browser column |
| `BROWSER_SHARE` | 0.35 | Browser share of the width left beside the navigation |
| `PAGE_MIN_WIDTH` | 420 | Smallest detail region |
| `FIELD_MIN_WIDTH` | 200 | Smallest label-field column in the page form |
| `SHELL_WIDE_MIN` | 1100 | Three-region breakpoint |
| `SHELL_MEDIUM_MIN` | 1024 | Browser-and-detail breakpoint |
| `HEADER_HEIGHT` | 48 | Shared height of the three aligned headers |

At `SHELL_WIDE_MIN` and above the navigation, browser, and detail are side by side. Between
`SHELL_MEDIUM_MIN` and `SHELL_WIDE_MIN` the navigation moves behind a transient toggle. A narrower
presentation shows one region at a time. The browser is the root and Back returns to it from the
detail. The shell follows the last region the user worked in, so narrowing the window during an
edit keeps the edit screen; choosing a destination returns to the browser. The browser takes its
share of the remaining width, the detail takes every remaining pixel, and neither has a maximum
width. Page content fills the detail card, and long forms wrap their fields instead of clipping, so
every region adapts to the space the shell actually gives it.

## 🧱 Workspace regions

The workspace has three regions with one owner each:

| Region | Owns | Surface |
| --- | --- | --- |
| Navigation | Destinations, counts, the Review entry, the vault identity, and the primary menu | Sidebar |
| Browser | The active destination's title, actions, list, calendar, or review queue, plus the permanent global search row | Window |
| Detail | The page or focused flow with its toolbar | Note view |

The three headers share `HEADER_HEIGHT` and align horizontally. The navigation header holds the
vault name and the primary menu. The browser header holds the destination title, refresh, and the
destination's actions. A dedicated full-width search row directly beneath the browser header holds
the permanent global search entry and its clear action. The detail toolbar holds Back, the page or
flow title, at most one suggested action, and a secondary menu.

Search is a browser filter, never a navigation location: the navigation keeps its destinations and
counts without a Search row. While a query is active, the browser title reads **Search Results** and
the destination-specific controls (Inbox composer, References action, Log date controls, Review
queue, Empty Trash) are hidden so one origin-independent result list fills the browser. A Trash result
appears in its own result group and opens read-only.

The primary menu sits above the navigation list, as required when a window has a sidebar. The
navigation is a bordered panel with the reference surface radius: structural in the wide layout, and
elevated with a shadow when it becomes a drawer. The browser is flush with the window surface. The
detail keeps the note-view surface and its card boundary.

A third-party desktop window supplies its own decorations. The application cannot draw controls
into the title bar, so the in-window headers are the structural equivalent of the reference header
bar. The application never mimics a custom title bar.

## 🎯 Accent, actions, and selection

The accent supplies suggested-action fills, focus rings, and links. It is not the selection color.
A selected navigation row uses a neutral 10% `ON_SURFACE` shade with no accent tint and no accent
edge, matching libadwaita's `.navigation-sidebar` treatment. The label and icon remain the identity
of the row; the value step is the selection cue.

Destructive actions use Red 3 in light mode and Red 4 in dark mode. An irreversible confirmation
carries the destructive style. Trash is reversible: it moves immediately and offers Undo in a toast,
so it does not use a destructive confirmation. Restoring over an occupied birthplace, deleting one
entry permanently, and emptying the Trash are user-invoked and irreversible, so each uses a
confirmation with Cancel first. Scheduled retention is the non-user-invoked exception and has no
confirmation surface. The accent is never used to distinguish one browser section from another; log
marks use the accent.

## 🎚️ Control states

An affirmative action is insensitive until its input can succeed; the command still rejects invalid
input as a guard, but the interface does not invite a click that must fail. An insensitive control
uses the muted disabled fill and label rather than the accent, and availability updates as the field
changes. A rendered surface shows at most one suggested or destructive control, and a dialog or
inline panel counts on its own. A reversible action uses Undo in a toast instead of a confirmation.
An irreversible confirmation puts Cancel before the affirmative action, and the affirmative action
names the operation.

## 💬 Feedback

Feedback is chosen by the lifetime of the event, not by severity:

| Surface | Owns | Examples |
| --- | --- | --- |
| Toast | A one-time result, failure, or undo | Capture failed, page moved to trash, undo restored a page |
| Owned banner | A condition that remains true | Page conflict, refresh failure, unresolved leave guard |
| Inline text | A field or form problem | Invalid category, blank rename, form write failure |
| Panel or dialog | A decision or consequence preview | Rename preview, category move, type change, repair, Trash overwrite, Empty Trash |

A toast appears at the bottom center, stays dismissible, disappears on its own, and carries at most
one action. The action names the operation it reverses. A success toast appears only when the result
is not already visible in the page or list. A toast never reports a condition that remains true.

A banner is rendered from the state that owns the condition: the workspace owns vault and selection
conditions, the vault session owns scan and refresh failures, the page owns conflicts and blocking
state, and the processing state owns a post-apply refresh failure. A background refresh never clears
an owned banner or a waiting notice.

Trash moves a page immediately and offers **Undo** in a toast. Undo restores the note to its original
path when that path is free; an occupied path is reported and never overwritten. The undo opportunity
belongs to the current session and ends when the toast is dismissed or replaced. The **Trash**
destination identifies an entry by its title and `From` birthplace, never by its UUID storage name. Its
read-only page suggests **Restore** and keeps **Delete Permanently…** in the secondary menu. A trashed
note's success, failure, and retention surfaces never display the UUID.

Dialogs put initial focus on the first control, close on Esc, keep Cancel before an irreversible
affirmative action, and never make a destructive action the default. Menus and popovers stay small,
close on Esc, and need no Close or Done button. Confirmation panels stay inline with the page they
change; they are not moved into a modal.

## 🔤 Typography

`BASE_FONT_SIZE` is 15 logical pixels (about 11 pt). Every role is a percentage of that base, so the
whole hierarchy scales together.

| GNOME style | Base % | Size / weight | Use |
| --- | --- | --- | --- |
| `title-1` | 181% | 27 / 800 | Page title |
| `title-2` | 136% | 20 / 800 | Step headline and welcome |
| `title-3` | 136% | 20 / 700 | Page and section headings |
| `title-4` | 118% | 18 / 700 | Panels and groups |
| `heading` | 100% | 15 / 700 | Compact headings and control labels |
| `body` | 100% | 15 / 400 | Prose |
| `caption` | 82% | 12 / 400 | Metadata and captions |
| `caption-heading` | 82% | 12 / 700 | Section captions |

Views select a role from `theme.TEXT_ROLES` with `style=`. The Material `theme_style` names are not
part of the standard; the gate rejects them. The application does not bundle a font file: the
theme leaves the family unset so Flutter resolves the platform font, and the resolved family is
checked per platform at release.

## ✍️ Writing style

Copy follows the GNOME writing style. Headings, view and destination titles, dialog titles, buttons,
menu items, tooltips, and section labels use **header capitalization**: capitalize the first and last
word, every word of four or more letters, every verb and noun, and both parts of a hyphenated word.
Articles, conjunctions, and prepositions of three letters or fewer stay lowercase in the middle of a
label. Examples: **New Vault…**, **Move to Trash**, **Search Results**, **Due Step**.

Field labels, hints, dialog bodies, banners, and status messages use **sentence capitalization**:
capitalize the first word and proper nouns only. Examples: **Vault folder path**, **Due date**, **The
first line becomes the title**.

Copy does not end with a period, even when it is written as a complete sentence. Internal periods
remain in text that needs more than one sentence.

An ellipsis (…) marks only an action that opens a dialog, form, confirmation, or native picker before
it can complete: **New Vault…**, **Move to Trash…**, **Set Plan Date…**. The affirmative control
inside that surface carries no ellipsis because it completes the action immediately. Navigation
destinations, immediate actions, and informational dialogs such as About carry none.

Tone is neutral. First- and second-person pronouns are not used; **your** is avoided even where the
reference allows it, because no current string needs it. Command examples keep straight quotes
because they are typed syntax; prose uses typographic quotation marks.

The typographic apostrophe (’) and the single-character ellipsis (…) are mandatory.

## 📋 Lists and rows

Browser lists follow the reference list view rather than a card grid: a row keeps a heading title,
at most one body-weight supporting line, and one muted caption line for metadata. Rows use the
standard list-row height and padding; the dense treatment is not used. The standard row height and
the type roles carry the hierarchy, so a list does not become a wall of equally muted text. Row text
is not selectable: the row is one click target, so a text-selection surface must not sit inside it. A
preview link keeps the body style instead of the link underline and acts like a click on the row. A
selected row keeps the neutral selected-row fill; focus adds an accent ring and never a second fill.
The ring clears as soon as the open page is not that row, so no second row can read as a selection.

## 🖼️ Icons

Interface icons use monochrome symbolic or outlined glyphs at `ICON_SIZE` (16) or
`ICON_SIZE_LARGE` (32). A filled glyph is not used when an outlined variant exists. The toolkit's
Material icon set stands in for Adwaita's symbolic set; no custom SVG icon set ships.

## 🔀 Bounded differences

These five differences are toolkit limits, not design preferences. Adding another one requires a
change that updates this table and the `interface-theme` spec.

| Reference behavior | Afanes | Status | Why |
| --- | --- | --- | --- |
| Adwaita symbolic icons | Material symbolic/outlined glyphs, tinted in code | Permanent, asset-free | no bundled SVG set; platform parity |
| libadwaita widget rendering | Flet/Material widget internals: field labels, ink feedback, scrollbars, overlay chrome | Temporary, shrinking | Flet boundary; feedback colors, radii, and density are set centrally |
| Access-key mnemonics | No underlined Alt shortcuts | Permanent, Flet limit | Flet exposes no mnemonic API |
| High-contrast style | No separate high-contrast input | Permanent, Flet limit | Flet exposes no high-contrast input; Flutter exposes one |
| Header bar with window controls | Native title bar plus in-window headers | Permanent, Flet limit | Flet desktop windows use native decorations and expose no title-bar control API |

The platform typeface is **not** a difference: the typography guideline requires the system font.
The remaining obligation is to confirm the resolved family on each platform. If Flutter resolves to
Roboto instead of the platform family, the platform family is set explicitly or the platform
variation is recorded separately.

## ♿ Accessibility notes

Body, muted, and accent text meet 4.5:1 on their neutral surfaces. Two reference-inherited tensions
are documented rather than hidden:

- white on the `#3584E4` suggested fill is 3.77:1, so a label on that fill is treated as control
  text at 3:1, not as body text;
- the Red 4 dark destructive fill is 2.75:1 against the dark note view; the white label on it is
  6.1:1, and the action is identified by its label and shape as well as its fill.

High-contrast mode and access keys cannot be exercised through Flet today; both are declared
limits above. Large-text robustness and accessible names are tracked in wave 5.

## 🚦 The conformance gate

`tests/ui/test_conformance.py` scans `src/afanes/ui` and compares nine measurements with an
embedded baseline:

- color literals and `ft.Colors.*` outside the token module;
- hardcoded `ft.Text(size=...)`, `ft.TextStyle(size=...)`, or `font_size`;
- Material `ft.TextThemeStyle` role names;
- arbitrary `ft.Icon(size=...)` literals;
- filled icon glyphs that have an outlined variant;
- numeric layout literals outside the token module;
- suggested or destructive actions per view class;
- controls carrying both an icon and a label outside a header bar;
- `dense=True` rows.

Header-bar actions are exempt from the icon-or-label rule through an explicit key allowlist in the
gate; the spec allows the combination there, and a focused test asserts the allowlist matches the
controls actually placed in the toolbar.

The value rules count per module; the button rules count within each view class. That class scope is
a conservative upper bound for a class that owns several dialogs, so view-level tests check the
rendered surface for the one-action rule. The comparison fails in both directions. A count above its
baseline entry is a new violation; a baseline entry above the measured count is stale and must be
deleted in the same change. The baseline is a debt ledger: it starts at the values measured when the
gate landed and must reach empty before the standard is complete. Never add an entry to make a
change pass. The icon-or-label and dense-row ledgers are empty after wave 2.

### 🧪 The copy gate

`tests/ui/test_copy.py` scans `src/afanes/ui/strings.py` and `src/afanes/cli/strings.py`. It applies
the mechanical rules to every string literal and the capitalization rules to the constants and
mapping values declared in its header-case and sentence-case sets. A name without a declared style
fails the gate. The ellipsis rule requires every `…` string to appear in the declared further-input
action set, and every member of that set to carry the ellipsis.

The gate has no baseline: a copy violation is either fixed or the change is not complete. Its
header-capitalization check cannot identify short nouns and verbs, so a lowercase three-letter
content word in the middle of a label remains a manual-review catch.

## 🧭 Migration waves

Wave 0 landed with the change that introduced this standard. Later waves are separate changes with
their own spec deltas:

```text
WAVE 0  tokens, two palettes, four surfaces, neutral selection, GNOME type
        scale, outlined icons, 1024x600 minimum, expanded gate
WAVE 1  landed: three regions, aligned headers, global search, primary menu,
        max content width, panel/radius/spacing sweep
WAVE 2  landed: control hierarchy: one suggested or destructive action
        per rendered surface, icon XOR label outside header bars,
        standard list rows, insensitive invalid actions, cancel-first
        confirmations
WAVE 3  landed: writing style: header capitalization, ellipses, final periods,
        neutral tone, typographic apostrophes and ellipsis, copy gate,
        AGENTS.md 4.6
WAVE 4  landed: feedback: undo over confirmation, toasts for one-time events,
        banners only for persistent states, overlays
WAVE 5  keyboard and accessibility: shortcut map, focus order, semantics
        labels, large-text robustness
WAVE 6  landed: breakpoints, collapsible navigation, narrow and large-window
        behavior; the remaining adaptivity work is per-view polish
WAVE 7  identity: app icon, placeholder pages, final palette pass, empty
        baseline
```

Waves are ordering, not exemptions. The target remains strict conformance; the five Flet limits
above are the only permanent exceptions.

## ✅ Changing the standard

A visual change gets its own OpenSpec change. It must say which level it touches, whether it adds a
difference, and how the gate and baseline move. If the change removes a baseline entry by migrating
the offending code, it deletes that entry in the same commit.
