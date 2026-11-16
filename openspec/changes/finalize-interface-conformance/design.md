# Design

## Context

Wave 7 is the last HIG conformance wave. The current tree has no application icon asset, empty
browser and detail states are unlabeled muted text, and high contrast is recorded as a permanent Flet
limit. Flet 1.1.2 exposes `SemanticsService.get_accessibility_features()` and reports
`high_contrast`; a local probe returned the full feature object on this Linux desktop. The theme is
composed from `LIGHT_THEME`/`DARK_THEME` constants and the views consume Material color roles, so a
high-contrast variant can swap the page themes without rewriting every view.

## Goals / Non-Goals

**Goals:**

- Ship one original SVG identity icon that the Flet build discovers under `src/assets/`.
- Replace plain empty messages with one shared symbolic placeholder page used by the browser and the
  no-page detail.
- Detect platform high contrast and apply light or dark high-contrast palettes at startup and after a
  resume.
- Remove high-contrast mode from the bounded differences and keep the conformance baseline empty.

**Non-Goals:**

- Redesigning the first-run welcome surface, which is an initial-state surface rather than an empty
  content view.
- Adding illustration placeholders or custom symbolic interface icon sets.
- Adding a user-facing contrast preference; the platform setting remains authoritative.
- Building or publishing desktop artifacts; the packaging prerequisites remain a separate gate.

## Decisions

### One presentational placeholder component

`ui/components/placeholder.py` owns a small `PlaceholderPage` class. It receives a symbolic icon, a
heading, an optional guidance line, and an optional action control, and returns a centered
`ft.Container` with one `ft.Column`. The icon uses `ICON_SIZE_LARGE`, the muted color, and no
semantics label so it remains decorative; the heading and guidance carry the accessible text.
Callers own the copy and the decision to show it.

The workspace uses it for an empty destination, an empty search, and empty Trash. `PageView` uses it
when no page is open. The Log tree keeps its compact empty line because the calendar still fills its
view. A focused flow or an owned banner takes precedence and suppresses the placeholder.

Copy is added to the English source and the tracked Spanish `.po` catalog, with one heading and one
guidance line per context. Actions are optional and must not duplicate an action already in the
browser header.

Alternative considered: a free-standing helper in the workspace. Rejected because the view-helper
gate forbids duplicate empty-state builders and the page view needs the same surface.

### High contrast is selected from the platform report

`AppShell` owns one `ft.SemanticsService` added to `page.services`. It queries
`get_accessibility_features()` during startup and again when
`page.on_app_lifecycle_state_change` reports a resume. The result selects a high-contrast light or
dark palette; a failed query falls back to the standard palette and never blocks the workspace.

`ui/theme.py` gains a `build_theme(palette, *, dark)` function used to build the standard themes and
the high-contrast variants. The high-contrast palettes keep pure light or dark surfaces, stronger
outlines, and body text at or above 7:1. The explicit Material roles in views continue to follow
`page.theme` and `page.dark_theme`; no per-view high-contrast branch is added.

Alternative considered: polling the feature service on a timer. Rejected because there is no change
event and resume is sufficient for a desktop session; a timer would add work without a stronger
contract.

Alternative considered: a manual in-app contrast preference. Rejected because it duplicates the
operating-system setting and creates a second source of truth.

### The identity icon is a text SVG

`src/assets/icon.svg` is an original, framed, rounded application mark with a page silhouette and a
check mark. It uses a `viewBox`, no text, no script, no external reference, and no embedded raster
data. Flet's build resolver accepts SVG sources and rasterizes them per platform, so the repository
keeps its no-binary-assets rule. The interface icon set stays Material symbolic glyphs.

The asset test parses the SVG as XML and checks the viewBox, forbidden elements and attributes, and
the absence of external URLs. A packaging task verifies that the Flet icon resolver discovers the
file when the build toolchain is available; until then the release evidence records the standalone
asset check only.

### Bounded differences shrink from six to five

The high-contrast row leaves the table because the platform flag is now consumed. The remaining five
are the symbolic icon substitution, Flet widget rendering, access-key mnemonics, native title bar,
and anchored calendar popover. The interface standard, README, and `RELEASE.md` describe the reduced
list; the conformance baseline stays empty.

## Risks / Trade-offs

- **The accessibility feature call may fail or report staleness on a platform.** It falls back to the
  standard palette and is re-read on resume; the application never blocks on it.
- **A theme swap can leave an explicit view color behind.** High-contrast tests check palette contrast
  and the rendered gate checks geometry; a manual light/dark high-contrast pass remains release
  evidence.
- **Flet may reject the SVG during packaging even though the resolver supports it.** The implementation
  verifies the resolver directly and records the asset-only check until the native toolchain is
  available; a rejected icon blocks the change rather than shipping the default.
- **Placeholder pages can duplicate header actions.** The component accepts at most one action and the
  browser callers omit actions already present in the header.
- **A resume event is not a guaranteed color-scheme event.** The palette is re-read on the next resume
  and at every new launch; no polling is added.

## Migration Plan

No vault, schema, CLI, or dependency migration. Existing installations keep their vaults and
preferences. Rollback is reverting the source change; the icon and placeholder copy are additive.
