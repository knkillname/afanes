# Design

## Context

See `proposal.md` for motivation. The current interface has three useful foundations:

- `AppShell._on_keyboard` already owns page-level routing for `Ctrl+F`, `Ctrl+N`, and Esc.
- `DatePickerDialog.handle_key` already defines the full keyboard contract and
  `CalendarGrid` already paints focus on a day cell.
- `ProjectsView` already demonstrates the focusable-row pattern with a `TextButton`, a focus ring,
  and programmatic `focus()`.

The remaining gaps are architectural rather than visual: the Log calendar has no keyboard adapter,
Review cards are clickable `Container` controls, `Dialogs.trash_page` returns to the browser without
a focus target, accessible names are inconsistent, and large-text layout has no automated oracle.

The layout oracle uses the cached Flet desktop client, not `flet test`: Flutter and the Linux build
toolchain are absent, `flet test` would add `numpy` and `scikit-image`, and committed screenshot
goldens would conflict with the rule that documentation screenshots are the only tracked binaries.

## Goals / Non-Goals

**Goals:**

- One shortcut sheet that is discoverable from the primary menu and `Ctrl+?`.
- One day-view keyboard contract shared by the date picker and the Log calendar.
- Keyboard access to Review cards and a predictable focus target after trashing a page.
- A clean-sheet accessible-name gate and live regions for messages.
- An automated 200% layout snapshot that fails without a person inspecting pixels.
- Linux release evidence for the real GNOME Large Text setting.

**Non-Goals:**

- Automating the operating-system Large Text switch. That remains manual evidence.
- Replacing the Flet desktop client with Flutter integration tests.
- Committing screenshot goldens.
- Adding user-visible text-size controls or a new runtime dependency.
- Changing the shortcuts that browsers may intercept; the web caveat is documented instead.

## Decisions

### Shortcut sheet is a presentational component owned by the shell

A new `ui/components/shortcuts.py` component renders the grouped sheet from the active `UiCopy`.
`WorkspaceView` adds **Keyboard Shortcuts…** to the primary menu and forwards it through an
`on_shortcuts` callback. `AppShell` owns the dialog lifetime, consistent with the existing About
dialog and date picker. It closes on Esc and puts initial focus on **Close**.

`AppShell._on_keyboard` accepts `Ctrl+?` by matching the normalized `?` key and the shifted `/` key
used by layouts where `?` is not reported directly. On web, the same chord may be intercepted by the
browser; the guide records that limit rather than inventing a different desktop shortcut.

Alternative considered: a separate **Help** destination. Rejected because the sheet is transient,
small, and belongs with About in the primary menu.

### Log calendar gets a day-only keyboard adapter

`CalendarGrid` already owns focusable day buttons and a `focused_day` record. A small
`LogCalendarKeyboard` adapter in `ui/components/calendar.py` maps arrows to one day or one week,
Page Up/Page Down to one month, Home/End to the week bounds, and Enter to the selected day. It calls
the existing `focus_day()` and `on_select` paths, so pointer and keyboard selection stay identical.

`WorkspaceView` exposes a keyboard command that returns `True` only when the Log calendar owns focus.
`AppShell._on_keyboard` offers the event to the workspace before the global shortcuts. Tab is never
trapped; focus can leave the grid.

Alternative considered: sharing the date picker's month and year movement wholesale. Rejected because
the Log calendar is day-only and the picker's precision modes would add unused branches. The key
names and movement semantics remain the same.

### Review cards reuse the existing focusable-row pattern

The Review card becomes a focusable button row with the same focus-ring contract as a project row:
the accent ring follows `on_focus`/`on_blur`, the card remains selectable by pointer, and the current
item keeps the neutral selected fill. The row is not a new generic component until a third caller
needs the same behavior.

Focus after trashing is view-owned. Before the trash command runs, `WorkspaceView` records the note
paths in the current browser order. After the refresh and `navigation.back()`, it finds the removed
path and focuses the next row, the previous row when there is no next, or the search field when the
browser is empty. The state command remains responsible for the write and returns whether the move
succeeded; the view owns control focus.

Alternative considered: putting focus recovery in `Dialogs.trash_page`. Rejected because state has no
control references and a view-only concern would leak into the state layer.

### Accessible names are a clean-sheet static gate

A new accessibility test scans the UI source and control tree for interactive controls. A control
must obtain its name from one of:

- its visible text content;
- a tooltip on an icon-only action;
- an explicit `Semantics` label; or
- a `ListTile` title for a row.

Containers with `on_click` that are not buttons must be wrapped in a focusable `Semantics` or replaced
by a button. The gate has no baseline. Decorative icons and non-interactive containers are exempt by
rule, not by allowlist.

Banners and toasts wrap their message surface in `ft.Semantics(live_region=True)`. Visible text
remains the accessible name; one live region exists per message surface to avoid duplicate
announcements. Inline validation text is included when it is the primary error surface.

Alternative considered: a baseline of known missing names. Rejected because the change is the point at
which the interface becomes clean; a baseline would preserve the gap.

### The automated 200% oracle is a rendered layout snapshot

A test-only harness launches the real Afanes shell with the cached Flet desktop client and a
test-only theme scale of 200%. It does not change the shipped theme or add a user preference. The
harness records `on_size_change` geometry for keyed controls and structural regions in every primary
view at 100% and 200%, plus temporary screenshots for failure diagnosis.

The pass conditions are:

- every primary view is present and has a non-zero area;
- every text-bearing control grows when its text scale doubles, unless it is a deliberate
  single-line ellipsis control;
- no keyed control collapses or leaves its expected region;
- the 200% snapshot matches the committed JSON layout snapshot within a small pixel tolerance;
- no render exception occurs during the scripted tour.

The JSON snapshot is text, not an image. Screenshots are written only to a temporary directory and
are never committed. The harness is a separate Hatch command because it needs a display and must not
make the ordinary test suite depend on a running desktop session. Linux is the required snapshot for
the `1.0.0` gate; other platforms may add their own snapshots later.

Alternative considered: pixel goldens. Rejected for wave 5 because they would add tracked binaries,
require a policy exception, and churn with font and renderer changes. A Dart render-box harness is the
stronger long-term option once the Flutter toolchain is part of packaging; it is explicitly deferred.

### Documentation follows the behavior

`docs/guide/workspace.md` gains the shortcut sheet, `Ctrl+?`, the browser caveat, Review card focus,
and the post-trash focus rule. `docs/guide/log.md` gains the Log calendar keyboard table.
`docs/guide/dates.md` points to the shared day-view contract. The interface standard records the
accessibility gate and the automated layout snapshot as wave 5 evidence.

## Risks / Trade-offs

- **A layout snapshot can miss a subtle clip inside a box that grew.** Mitigation: check 100%/200%
  growth for text-bearing controls, keep the manual system Large Text pass, and make the snapshot
  cover every primary view rather than a sample.
- **The Flet desktop client needs a display and is Linux-only in practice.** Mitigation: keep the
  harness behind a dedicated Hatch command and require it only for the Linux release gate.
- **`ft.Screenshot` on the desktop client is not yet proven in this project.** Mitigation: make
  screenshots diagnostic only; the JSON geometry snapshot is the gate. If capture is unreliable,
  drop screenshots without changing the spec.
- **`Ctrl+?` can be intercepted by a browser.** Mitigation: document the desktop-first contract and
  keep the menu entry as the universal path.
- **Focus after trash is ambiguous across grouped sections.** Mitigation: define the target as the
  rendered browser order and fall back to the previous row, then the search field.
- **Live regions can become noisy.** Mitigation: announce only banners, toasts, and primary inline
  validation messages; do not announce every refresh or count change.
- **The accessible-name gate can false-positive on decorative controls.** Mitigation: encode
  decorative exemptions as explicit structural rules, not a growing allowlist.

## Migration Plan

Wave 5 is one UI change series with no vault or schema migration. Rollback reverts the UI, i18n,
tests, and documentation; no note, vault, or public API data changes. The layout snapshot JSON is a
test fixture and is regenerated only after a reviewed large-text pass.

## Open Questions

None that change the approach. The exact snapshot tolerance and the decision to keep or drop
diagnostic screenshots can be settled during implementation without changing the specs or task
sequence.
