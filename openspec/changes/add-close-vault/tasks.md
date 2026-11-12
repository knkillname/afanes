# Tasks

## 1. Preferences removal

- [x] 1.1 Add `SettingsStore.clear()` that removes the settings file, treats a missing file as success, and raises `ConfigurationError` naming the path on failure; verify tests for an existing file, a missing file, and a failing unlink
- [x] 1.2 Verify clearing preferences never reads or writes the vault and leaves a valid settings file for a later open when the removal fails

## 2. Controller close

- [x] 2.1 Add `AppState.close_vault()` that takes the command lock, commits the open page, clears the remembered preferences in a worker thread, and calls `_show_welcome`; verify a close without a page and a close with a dirty page
- [x] 2.2 Refuse the close when the page has a pending dialog or disk conflict, leaving the vault open and the existing message in place; verify each blocking case
- [x] 2.3 Show the welcome state with a message when preferences cannot be removed, and keep the session guard claimed; verify both

## 3. Interface

- [x] 3.1 Add the `Close vault` menu item and an `on_close_vault` callback to the workspace change menu; rename the other items to `Open another vault` and `Create a new vault`
- [x] 3.2 Route the shell's close through the controller and re-render the welcome state; verify the view test and the app test for the menu item
- [x] 3.3 Add centralized copy for the action and both failure messages; verify no view or shell writes the copy inline

## 4. Validation

- [x] 4.1 Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, and the prohibited-vocabulary check
- [x] 4.2 Verify closing a vault that no longer exists, or whose settings file is already gone, still returns to the welcome state without writing vault content

## Workflow follow-up

- Archive the change once review requirements are satisfied.
- Update `CHANGELOG.md` during the release workflow, naming the close action and the forgotten preference.
