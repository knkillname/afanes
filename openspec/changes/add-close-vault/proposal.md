# Proposal

## Why

Once a vault is open there is no way to close it. The welcome state, which is the only place that
offers "New vault", is unreachable without quitting and relaunching the application. A user who
wants to stop working in one vault and start fresh has to restart the process, and a user who
opened the wrong folder has no escape at all.

## What Changes

- Add a **Close vault** action to the workspace change-vault menu. It saves an open page draft,
  clears the session's vault, forgets the remembered vault, and shows the welcome state.
- **Forget the remembered vault** by deleting the application's settings file. The next launch
  starts at the welcome state instead of reopening the vault.
- **Block the close** when the open page has a pending conflict or dialog, using the same checks
  already applied when switching vaults. The vault stays open and a message explains what to
  resolve.
- **Report a preferences failure without stranding the user**: if the settings file cannot be
  removed, the welcome state is still shown and a message says the vault may reopen next launch.
- Clarify the two existing change-vault menu items: **Open another vault** and **Create a new
  vault**, so the creation path that offers starter content is not confused with opening one.
- Keep the close action out of the welcome state and out of the command line. It is a session
  action and never changes note content beyond saving an open draft.

Non-goals: applying templates, deleting or moving a vault directory, clearing the SQLite cache,
changing the note format, adding a command-line `close` command, and releasing the single-session
guard.

## Capabilities

### Modified Capabilities

- `vault-selection`: the workspace gains an explicit close action with its draft-save, forget, and
  failure behavior, plus the clarified change-vault labels.

## Impact

- **Core**: `SettingsStore` gains a `clear` operation that removes the app-owned settings file. It
  never touches the vault.
- **Interface**: `AppState` gains a close command that reuses the existing draft-commit checks;
  the shell renders the welcome state afterward; the workspace menu gains the action and clearer
  labels.
- **Tests**: settings removal cases, close with and without a dirty page, blocked close, settings
  removal failure, session guard, and menu routing.
- **Compatibility**: no note-format change, no new dependency, no network access. Vaults are
  untouched apart from an intentional draft save. Preferences are removed only when the user asks
  to close, which is the requested behavior.
- **Documentation**: a changelog entry during the release workflow.
