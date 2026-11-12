# Spec Delta

## ADDED Requirements

### Requirement: The current vault can be closed

From the workspace change-vault action, the user SHALL be able to close the current vault. Closing
SHALL save a dirty open page, clear the session's vault, forget the remembered vault so the next
launch starts at the welcome state, and show the welcome state. Closing MUST NOT release the
single-session guard, and MUST NOT modify the vault apart from the open page save.

#### Scenario: Close returns to the welcome state

- **WHEN** the user closes the current vault
- **THEN** the workspace is replaced by the welcome state and no vault is open

#### Scenario: Close forgets the remembered vault

- **WHEN** the user closes the current vault and starts the application again
- **THEN** the welcome state is shown instead of reopening the vault

#### Scenario: Dirty page is saved before closing

- **WHEN** the open page has unsaved edits and the user closes the vault
- **THEN** the edits are saved and the vault closes

#### Scenario: A pending page action blocks the close

- **WHEN** a page dialog or disk conflict is pending and the user closes the vault
- **THEN** the vault stays open, the current screen remains, and a message explains what to
  resolve

#### Scenario: Preferences cannot be cleared

- **WHEN** the vault is closed but the remembered preferences cannot be removed
- **THEN** the welcome state is shown and a message says the vault may reopen on the next launch

#### Scenario: Closing writes nothing else

- **WHEN** the user closes the vault
- **THEN** no note other than an unsaved open page is created, renamed, moved, or trashed

#### Scenario: The session guard survives a close

- **WHEN** the user closes the vault
- **THEN** the window keeps the single active session and does not release it
