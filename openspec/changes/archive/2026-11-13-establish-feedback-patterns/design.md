# Design

## Context

See `proposal.md` - Why. The current feedback path is one mutable `UiStatus.message` slot that five
views render as a `Banner`. The slot has no owner, so a successful command can clear a conflict that
is still true. The browser contract already requires a visible message to survive a background
refresh, which this slot cannot guarantee.

The trash flow is split between `PageDialogState` (`begin_trash`, `apply_trash`, `cancel_trash`,
`trash_preview`) and `TrashPanel` in `ui/components/page_panels.py`. The page menu label carries an
ellipsis because it opens that panel. `VaultNaming.trash` returns an inbound-reference count and
moves the file with `Path.replace`. There is no undo path.

The interface uses Flet `AlertDialog` for vault, reference, log, role, and date surfaces, and
`PopupMenuButton` for the primary and page menus. Flet 1.1.2 provides `SnackBar` as a
`DialogControl` with a duration, a close icon, and one action, so the toast does not need a custom
timer or overlay stack.

## Goals / Non-Goals

**Goals:**

- Make the feedback channel a property of the event lifetime, not a single global slot.
- Give every persistent condition one owner and one render location.
- Make trash immediate and reversible within the current session.
- Keep the inline confirmation panels and audit the existing dialogs and menus as overlays.
- Leave the vault format, note format, and CLI unchanged.

**Non-Goals:**

- The Trash sidebar, the 30-day purge, trash frontmatter metadata, and the schema binder; those are
  a separate follow-up change.
- A notification center, OS notifications, or a persistent feedback history.
- A custom toast surface or a replacement for Flet's dialog/popover stack.
- Changing rename, category move, type change, processing, conflict, or repair into undo flows.
- New visual styling outside the existing token system.

## Decisions

### D1. Separate the transient notice from the persistent banner

`UiStatus` loses `message` and `show_message`. It keeps `busy` and `session_active` and gains a
transient `notice`:

```python
class NoticeAction(StrEnum):
    UNDO_TRASH = "undo-trash"

@dataclass(frozen=True, slots=True)
class Notice:
    message: str
    action: NoticeAction | None = None
```

`UiStatus.show_notice(message, action=None)` stores the latest notice; `take_notice()` returns it and
clears it, so a view consumes it once. A second notice replaces the first; toasts are transient and
do not need a queue. The latest-wins rule is explicit in the method docstring.

Persistent banners are not stored in `UiStatus`. Each owner exposes one optional banner string:

- `WorkspaceController` owns the vault/selection condition shown on the welcome surface.
- `VaultSession` owns the scan/refresh failure.
- `PageEditorState` owns the page conflict and the blocking message that prevents leaving.
- `ProcessingState` owns the post-apply refresh failure.

A view that needs a banner reads the specific owner. The workspace shell renders the session,
workspace, and processing banners; the page view renders the page banner. That gives each condition
one render location and prevents the shell and the page from showing the same string twice.

Alternatives considered:

- keep a global banner slot and add a clear-owner discipline: the slot can still be cleared by an
  unrelated command, and the browser's refresh contract stays hard to prove;
- one feedback controller with a list of active banners: an extra collaborator and an `AppState`
  field, while the condition already lives in a state object;
- keep `show_message` and classify call sites with a test: the generic API still permits the wrong
  lifetime and the classification table becomes a second source of truth.

### D2. Use Flet `SnackBar` through a small presenter

`ToastPresenter` is a UI component owned by `AppShell`. It holds the page and the current snackbar:
`show(notice)` closes the previous snackbar by setting `open = False`, then calls
`page.show_dialog(SnackBar(...))`. It uses `SnackBarBehavior.FLOATING`, `show_close_icon=True`, a
duration token, the themed overlay surface and text colors, and one `SnackBarAction` when the notice
carries an action. The action callback maps `NoticeAction.UNDO_TRASH` to the dialog state's undo
command.

The presenter never calls `page.pop_dialog()`: that would close the topmost dialog and could dismiss
a vault or reference dialog instead of the toast. It keeps its own reference and closes only that
control.

`WorkspaceActions` gains an `on_notice` callback. `WorkspaceView._refresh_dynamic` calls
`state.status.take_notice()` and forwards the notice to the presenter. Dialog commands already call
`_refresh_current_workspace`, so a notice set by a dialog command is consumed after the dialog
closes. Dialog validation stays inline and does not raise a toast while the dialog is open.

Alternatives considered:

- a custom workspace toast with an `asyncio` timer: full styling control, but it adds a task
  lifecycle, cancellation on dispose, and a second overlay stack; the Flet widget already supplies
  the behavior and the bounded-difference table already covers overlay chrome;
- a page-level custom `Overlay` entry: still needs a timer and does not improve the native
  dismissal.

### D3. Trash is immediate; undo owns the recovery path

The page's trash command plans and applies in one command. It commits the draft, plans the trash,
moves the note, clears the page, updates history, refreshes the scan, stores the resulting
`TrashPreview` as the current undo record, and emits a `Moved to Trash` notice with
`NoticeAction.UNDO_TRASH`. It does not read or report inbound references.

`VaultNaming.trash` changes to return the `TrashPreview` it actually used instead of an `int`. That
gives the caller the exact trash destination without a second plan that could race a filename
collision. The processing path ignores the return value; its tests update.

A new `VaultNaming.restore_from_trash(preview, confirm=True)` validates both paths against the vault
root, refuses a missing trash file, refuses an occupied source path, creates the original parent
directory when missing, and publishes the restored file without overwriting. The publish is
exclusive: a hard link to the source fails if the path exists, with an exclusive-copy fallback for
filesystems without hard links. The trash path is removed only after the source is published.

The undo record is one slot in `PageDialogState`, cleared when a new trash replaces it and when a
successful undo completes. A dismissed or replaced toast leaves the record unreachable; the next
trash overwrites it. The record is not persisted, so undo is a current-session action. The follow-up
trash room adds the persistent index, sidebar, and **Restore As…** path for a collision.

Alternatives considered:

- keep `trash()` returning the reference count and plan separately: the UI may hold a preview whose
  destination differs from the actual move;
- store the undo record in `UiStatus`: it is page state and would mix a durable command record with
  transient presentation;
- persist the undo record now: that is the trash-room data model and would pull the schema change
  into this change.

### D4. Classify feedback at the command site

The migration follows one rule: the command that knows the lifetime chooses the channel.

- A command that completes a one-time action and whose result is not already visible calls
  `show_notice`. Capture, rename, type change, category move, and review advancement remain quiet
  because their result is visible in the list or page.
- A command that fails once calls `show_notice`. A failure that leaves an open form stays inline in
  that form when the form can correct it; a field validation always stays inline.
- A condition that remains true writes the owning state's banner field. A successful resolution
  clears only that field.
- A decision keeps its existing inline panel or dialog. Trash is the only confirmation removed.

The page's category and rename-label validation moves inline. The dialog commands keep their
existing inline error fields. The processing plan/apply failures become toasts while the form
remains; the post-apply refresh failure becomes the processing banner because the wizard has
already closed. The review form keeps its form error inline; the card-level failures become toasts.
The session's refresh failure becomes its banner; capture and preview failures become toasts.

Alternatives considered:

- move every error to a toast: loses the form-local context the user needs to correct the input;
- keep every non-refresh error as a banner: leaves one-time failures on screen until another
  command clears them, which is the current problem;
- add a generic `Feedback` service with a severity parameter: the lifetime, not the severity, is
  the decision the call site knows.

### D5. Audit overlays without replacing the Flet stack

Dialogs remain `AlertDialog`; the audit checks each one for initial focus, Esc dismissal through
`on_dismiss`, Cancel before the affirmative action, a specific affirmative label, and no destructive
default. The shared pattern stays in the existing dialog components; the vault and reference
dialogs keep their inline error fields.

Menus remain `PopupMenuButton`. The audit checks that the primary and page menus close on Esc and
stay small; the template picker remains a form dropdown, not a popover.

The toast is the only new overlay. It uses the themed overlay surface, text, and action colors. The
inline confirmation panels stay inline because the HIG treats action dialogs as disruptive and the
existing panels keep the consequence preview in context.

Alternatives considered:

- move the inline panels into modals: contradicts the HIG preference for inline actions and
  interrupts the page the user is working in;
- replace Flet's dialogs with custom surfaces: the archived standard change explicitly rejects this
  as a non-goal and the bounded-difference table covers the widget chrome.

### D6. Keep the gates honest

`tests/ui/test_copy.py` gains the new toast, undo, and restore constants and drops the retired trash
panel constants. `PAGE_TRASH` loses its ellipsis and leaves `ELLIPSIS_ACTIONS`; the trash action now
completes immediately. The `tests/ui/test_conformance.py` baseline loses the removed `TrashPanel`
entry; the toast action is a `SnackBarAction`, not a filled button, so the one-action budget is not
changed. Any numeric layout literal in the toast component is expressed as a token.

A focused `tests/ui/test_feedback.py` covers the notice lifecycle, the presenter's snackbar
parameters, toast replacement and dismissal, trash undo, occupied-path refusal, and the ownership of
each banner. Existing view tests are updated to assert the channel rather than the old global
message.

Alternatives considered:

- a static scan that every call site is classified: the method split already makes the wrong call
  impossible to spell;
- leave the copy gate to fail on the new constants and fix it later: the gate has no baseline, so
  the change would not be complete.

## Risks / Trade-offs

- [Undo is lost on restart and the trash room is a later change] -> Document the current-session
  limit; keep the note safe in `trash/`; the follow-up change adds the persistent destination and
  restore path.
- [Flet `SnackBar` is Material chrome and may cover a modal dialog] -> Show toasts from workspace
  commands only; dialogs keep their inline errors; style the surface with tokens; fall back to a
  custom host only if the visual review rejects it.
- [Removing the pre-trash reference warning hides a consequence] -> Undo restores the note and its
  references; the trash room will make unresolved references visible and offer restore.
- [Migrating ~90 generic message calls can misclassify a condition] -> Use the owner table in D4,
  keep the state-level tests per owner, and review the remaining `show_message` references before
  deleting the API.
- [A shell banner and a page banner can duplicate a string] -> One owner and one render location per
  condition; remove the view-local copies rather than forwarding the same string.
- [The toast presenter and the dialog stack can disagree about the topmost control] -> Never call
  `pop_dialog`; close only the presenter's own snackbar reference.
- [The trash room's schema work leaks into this change] -> The trash frontmatter, `afanes.yaml`
  section, retention, and sidebar are explicitly out of scope; the tasks verify no vault-format
  file changes.

## Migration Plan

1. Add `Notice`/`NoticeAction`, the `UiStatus` notice API, and the owner banner fields.
2. Add `ToastPresenter`, the `WorkspaceActions.on_notice` callback, and the AppShell wiring.
3. Change `VaultNaming.trash` to return the `TrashPreview`; add `restore_from_trash`.
4. Replace the page trash flow; remove `TrashPanel` and the retired copy.
5. Migrate command sites to toast, banner, or inline; remove the view-local banner copies.
6. Audit dialogs and menus; add the focused tests.
7. Update the copy gate, conformance baseline, docs, `AGENTS.md`, and changelog.

Rollback is a source revert: no vault file, schema, note format, or dependency changes. A trashed
note remains in `trash/` if the application is reverted mid-flow.

## Open Questions

None. The trash-room data model, retention setting, schema binder, and sidebar are deliberately
deferred to the follow-up change; the toast duration and inline error placement are design tokens
and implementation details.
