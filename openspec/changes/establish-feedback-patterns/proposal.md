# Proposal

## Why

Afanes still carries one global `UiStatus.message` slot that every view renders as a warning
banner. That slot mixes four different jobs: a persistent condition such as a page conflict, a
one-time failure such as a failed save, a validation problem such as an empty category, and a
reminder that the page cannot be left yet. Because the slot has no owner, an unrelated successful
command can clear a warning that is still true, and the browser's own contract already requires a
visible message to survive a background refresh.

There is no toast and no undo. Moving a note to trash asks for confirmation even though the move is
reversible, while one-time errors interrupt the page with a banner that stays until another command
clears it. Wave 4 of the interface standard is the feedback wave: undo over confirmation, toasts for
one-time events, banners only for persistent states, and a bounded overlay treatment. The later
internationalization work would otherwise localize inconsistent feedback copy twice.

## What Changes

- **Feedback channels.** Split feedback by lifetime: a transient toast for one-time events and
  undo, an owned banner for a condition that remains true, inline text for a field or form problem,
  and an inline panel or dialog for a decision. Remove the generic `show_message` API; `UiStatus`
  exposes `show_notice`, and each persistent condition is rendered from the state that owns it.
- **Toasts.** Add a Flet `SnackBar` presenter owned by the application shell. A toast appears at the
  bottom center, is dismissible, disappears on its own, and carries at most one action. One-time
  errors become toasts. A success toast appears only when the result is not already visible, so
  capture, rename, type change, and review advancement stay quiet.
- **Trash undo.** **BREAKING (UI):** moving a page to trash takes effect immediately and offers
  **Undo**; the trash confirmation panel, its copy, and the pre-trash inbound-reference report are
  removed. The page menu label loses its ellipsis because it no longer opens a surface. Undo
  restores the just-trashed note to its original path when that path is free; if it is occupied, the
  undo reports the collision and leaves the note in trash. The undo is available for the current
  session only; the later trash-room change adds the persistent trash destination and its metadata.
- **Owned banners.** A persistent condition is read from its owner: the page conflict and blocking
  state on the page state, the refresh failure on the session, the vault error on the workspace,
  and the post-processing refresh failure on the processing state. A background refresh can never
  clear them.
- **Overlays.** Audit the existing dialogs, menus, and popovers, and theme the toast with the
  existing tokens. Keep the inline confirmation panels for rename, category move, type change,
  conflict resolution, and repair. Dialogs keep Cancel first, a specific affirmative label, initial
  focus, Esc to cancel, and no default action on a destructive operation.
- **Copy gate and conformance.** Classify the new copy constants, remove the retired trash copy,
  update the ellipsis action set, and update the visual conformance baseline for the removed panel
  and the new toast component.
- **Documentation and rules.** Update `AGENTS.md` so a destructive action requires a confirmation or
  a visible undo path; state that a vault write is committed only after the user sees the feedback
  surface. Update the interface standard to mark wave 4 landed, the guide pages that describe trash,
  and the changelog.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `interface-theme`: add the feedback-lifetime, toast, owned-banner, inline-validation, and overlay
  requirements; remove the trash scenario from the confirmation rule.
- `note-editing`: trash is immediate and undoable; the page no longer previews inbound references
  before trashing.
- `note-identity`: trashing leaves inbound references unresolved without a pre-trash count; undo
  restores them.
- `vault-layout`: a just-trashed note can be restored by the page's undo action without broadening
  general trash recovery.

## Impact

- `src/afanes/ui/state/status.py`, the state collaborators, `ui/views/`, `ui/components/banner.py`,
  a new toast component, `ui/app.py`, and `ui/components/page_panels.py`.
- `src/afanes/ui/strings.py` and `tests/ui/test_copy.py` for the new and removed copy.
- `tests/ui/test_conformance.py`, `tests/ui/test_page_view.py`, `tests/ui/test_state.py`,
  `tests/ui/test_workspace_view.py`, `tests/ui/test_review_view.py`,
  `tests/ui/test_processing_view.py`, and a new focused feedback test.
- `AGENTS.md` sections 4.5 and 4.6, `docs/develop/interface-standard.md`, the affected guide pages,
  and `CHANGELOG.md`.
- No vault schema, note format, dependency, CLI, or runtime-network change. The Trash sidebar, the
  30-day purge, the trash frontmatter metadata, and the schema relaxation are a separate follow-up
  change.
