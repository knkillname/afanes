# Design

## Context

See `proposal.md` for motivation. `ProcessingState.begin()` is the only path that reads the capture
body and loads the vault template card catalog. `ReviewState._enter_current_review_item()` duplicates
the body and session setup but never loads the catalog. `ProcessingView` then builds the Template
options once in its constructor from `ProcessingState.cards`, so a wizard opened by review starts with
no card options.

Review entry runs while its own command lock is held, and `ProcessingState.begin()` also acquires that
lock. Calling `begin()` from review would nest the lock, set and clear the busy flag prematurely, and
apply Inbox membership and error-message rules that do not match review's skip-on-failure behavior.
The view must not perform file I/O; the state layer owns reading the catalog.

## Goals / Non-Goals

**Goals:**

- One state path loads a capture body and its template card catalog for every wizard entry point.
- The Template dropdown reflects the loaded catalog whenever the wizard refreshes, preserving a valid
  selection.
- Keep review's existing behavior of skipping a capture that cannot be read.

**Non-Goals:**

- Watching `templates/` for changes while the wizard stays open. The catalog remains a snapshot taken
  when the capture opens.
- Changing the card format, validation, browser dialogs, vault layout, or processing plans.

## Decisions

### Share capture loading inside `ProcessingState`

Add `ProcessingState.load(path)` that reads the body and catalog in worker threads and assigns the
wizard fields. `begin()` keeps its Inbox membership check, busy flag, and user-facing message, then
delegates the reads to `load()`. `ReviewState._enter_current_review_item()` calls `load()` inside its
existing lock and keeps its skip-on-failure message and loop.

- **Why:** both entry points get identical capture, card, and preview state, so a future entry point
  cannot forget the catalog.
- **Alternative rejected:** call `begin()` from review. The command lock is not reentrant, review uses
  different failure handling, and `begin()` manages the busy flag for its own caller.
- **Alternative rejected:** read cards in the view. Views stay presentational and would repeat file
  I/O on every repaint.

### Rebuild Template options on every refresh

`ProcessingView` gets a small private helper that rebuilds `template.options` from
`ProcessingState.cards` and validates the current key. `_refresh_dynamic()` calls it before showing
the form. The constructor stops building options; the first refresh populates them. A still-valid
selection is kept, and a selected card that disappeared falls back to `empty`.

- **Why:** the dropdown is populated from the current state snapshot every time it can appear, not
  only when the view object was created.
- **Alternative rejected:** populate only when the outcome changes to Reference or Later. Other
  refreshes already need the choices, and unconditional rebuilding is cheaper and simpler than
  tracking transitions.

### Keep the catalog as an open-time snapshot

Cards are read once when the capture opens, matching the rest of the wizard's snapshot behavior.
Reloading on every outcome change would add I/O and make the preview depend on files changing
mid-edit.

## Risks / Trade-offs

- [A card read failure in `begin()` previously escaped the read handler] -> `load()` runs inside the
  existing try block, so the failure now appears as the same actionable read message.
- [Rebuilding options on every refresh does repeated work] -> the catalog is an in-memory tuple of
  usually seven cards; no file I/O occurs during refresh.
- [A selected card can disappear between refreshes] -> the helper validates the key and falls back to
  Empty without writing anything.
- [`load()` is public but assumes a caller-held lock] -> its docstring states the caller owns the
  command lock and user-facing error handling.

## Migration Plan

None. The change touches in-memory UI state and tests only; no vault data, settings, or dependencies
change.
