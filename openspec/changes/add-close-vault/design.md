# Design

## Context

See `proposal.md` — Why. The relevant current state:

- `AppState` already owns every vault transition. `_open_vault_state` saves the current page with
  `_commit_current` before switching, and `_show_welcome` clears the session's vault, snapshot,
  browser, review, processing, and page state without touching the settings file or the session
  guard.
- `SettingsStore` owns one app preferences file outside the vault. `load()` returns `None` when the
  file is missing, and `save()` writes a vault path. There is no "no vault" representation and no
  removal operation.
- The workspace change menu is a `PopupMenuButton` with two items wired to the shell through
  `on_change_vault` and `on_create_vault`.
- The single-session guard lives in `_vault_session`; it is claimed by `begin_session` and must
  survive a close.

## Goals / Non-Goals

**Goals:**

- One close path that saves the draft, forgets the preference, clears the workspace, and keeps the
  session guard.
- A preferences removal that is safe when the file is already missing and reports a read-only
  configuration directory without leaving the user in the closed vault.
- Menu labels that make opening and creating visibly different.

**Non-Goals:**

- A command-line close command.
- Deleting or moving the vault directory, or clearing the index cache.
- A confirmation dialog for a reversible close.
- Any settings-format change.

## Decisions

### `SettingsStore.clear` removes the file instead of changing the format

`clear()` calls `Path.unlink(missing_ok=True)`, so a missing file is success. `OSError` becomes
`ConfigurationError` with the settings path in the message. The next launch sees no file and shows
the welcome state. Keeping `Settings` as a vault-path value avoids a schema version bump and keeps
`from_payload` strict.

*Alternatives:* writing `"vault": null` (changes the payload contract, `save` validation, and every
reader); a `closed` flag in settings (the file would still exist and every reader would need the
special case).

### Close reuses the switch checks

`AppState.close_vault` acquires the command lock and calls `_commit_current`, exactly like
`_open_vault_state`. A dirty draft is saved; a pending rename, trash, repair, type-change, or disk
conflict refuses the close with the message the page already uses. This keeps one rule for leaving
a page instead of adding a parallel path.

### A failed preferences removal still closes the session

If `clear()` raises, the vault is still cleared from the window and the welcome state is shown, with
a message saying the vault may reopen next launch. Stranding the user in a vault because a
configuration directory is read-only would defeat the action.

*Alternative:* keeping the vault open until preferences can be removed — makes a read-only config
directory a trap.

### The menu owns the action, the shell owns the transition

`WorkspaceView` gains an `on_close_vault` callback and a third menu item. It only forwards the
intent. `_Shell.close_vault` awaits `AppState.close_vault` and re-renders, so the welcome state is
built from the same path as a failed launch.

## Risks / Trade-offs

- **Forgetting the vault surprises someone who only wanted the welcome screen** → the action is
  named "Close vault", the user requested forgetting, and the vault files are never touched.
- **A delete failure leaves preferences behind** → the welcome state is still shown and the message
  names the consequence.
- **A close during a page conflict loses the draft** → `_commit_current` refuses the close and the
  existing conflict message is shown.
- **Windows file locking** → `unlink` can fail while another process holds the file; the failure is
  reported like any other configuration error, and the session still closes.

## Migration Plan

No data or settings-format migration. Existing vaults and existing settings are untouched until a
close is requested. Rollback removes the menu item, the controller command, and `SettingsStore.clear`;
a settings file removed by a close is recreated the next time a vault is opened or created.

## Open Questions

None.
