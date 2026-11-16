# Proposal

## Why

Wave 5 is the remaining keyboard and accessibility gap before `1.0.0`. Global shortcuts exist, but
there is no shortcut reference, the Log calendar lacks the date picker’s keyboard contract, Review
cards are pointer-only, focus is lost after trashing a page, accessible names are inconsistent, and
large-text layout has no automated gate.

## What Changes

- Add a **Keyboard Shortcuts** primary-menu item and a `Ctrl+?` shortcut that open one grouped sheet
  covering General, Calendar, and Navigation shortcuts.
- Give the Log calendar the date picker’s arrow, Page Up/Page Down, Home/End, and Enter contract.
- Make Review queue cards keyboard-focusable and move focus to the next note row after trashing a
  page, or the previous row when none follows.
- Require an accessible name for every interactive control, use live regions for messages where Flet
  supports them, and add a clean-sheet accessibility gate with no baseline.
- Add an automated 200% rendered layout snapshot using the cached Flet desktop client. It records
  key control sizes at 100% and 200%, compares them with a text snapshot, and fails when text-bearing
  controls do not grow or regions collapse. Screenshots remain temporary failure artifacts.
- Verify the real GNOME **Large Text** setting manually at the minimum window and both breakpoints;
  the automated snapshot covers the 200% layout, not the operating-system switch.
- Document the shortcuts, the browser caveat for intercepted keys, the Log calendar keys, and the
  accessibility behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `interface-theme`: adds keyboard discoverability, accessible names, live regions, and the automated
  large-text layout requirement.
- `vault-browsing`: adds the shortcut menu entry, Review-card keyboard access, and focus recovery
  after trashing a page.
- `note-log`: adds the Log calendar keyboard contract.

## Impact

- UI code in `src/afanes/ui`, interface copy in `src/afanes/i18n`, and tests under `tests/ui`.
- A test-only rendered layout harness for the cached Flet desktop client and a text JSON snapshot; no
  new runtime dependency and no tracked screenshot goldens.
- Documentation in `docs/guide/workspace.md`, `docs/guide/log.md`, `docs/guide/dates.md`,
  `docs/develop/interface-standard.md`, and `RELEASE.md`.
- No vault format, CLI, schema, network, telemetry, or cloud change.
