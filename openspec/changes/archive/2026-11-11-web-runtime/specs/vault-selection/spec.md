# Spec Delta

## MODIFIED Requirements

### Requirement: First launch requests a vault

On first launch, when no saved vault is available, the application SHALL present a welcome state
explaining that a vault is a folder of Markdown files and offering the vault selection action
available in the current presentation. Where a native directory dialog exists, that action SHALL
open it; in a browser session it SHALL be an entry field for an absolute path. It MUST NOT create or
modify any vault file before a vault is chosen.

#### Scenario: Welcome appears without settings

- **WHEN** the application starts and no settings file exists
- **THEN** it shows the welcome state and does not scan or write to any vault

#### Scenario: Choosing a folder opens it

- **WHEN** the user selects an existing directory in the native dialog
- **THEN** the application saves that directory as the vault and shows the Inbox

#### Scenario: Entering a path opens the vault in a browser session

- **WHEN** a browser session user enters the absolute path of an existing directory
- **THEN** the application saves that directory as the vault and shows the Inbox

#### Scenario: Rejected path keeps the welcome state

- **WHEN** the entered path is missing, is not a directory, or cannot be read
- **THEN** the welcome state remains, explains the problem, and no settings file is written

#### Scenario: Cancelling leaves the welcome state

- **WHEN** the user cancels the selection without choosing a directory
- **THEN** the welcome state remains and no settings file is written

### Requirement: The user can change vaults

From the Inbox, the user SHALL be able to choose a different vault without restarting, using the
selection action available in the current presentation. The new path SHALL be persisted, and the
previous vault MUST NOT be modified.

#### Scenario: Changing the vault

- **WHEN** the user chooses a different directory through Change vault
- **THEN** the Inbox shows the new vault and the new path is saved

#### Scenario: Changing the vault in a browser session

- **WHEN** a browser session user enters the path of a different directory
- **THEN** the Inbox shows the new vault and the new path is saved

#### Scenario: Cancelling keeps the current vault

- **WHEN** the user cancels the selection during a change
- **THEN** the current vault remains active and the saved path is unchanged

#### Scenario: The previous vault is untouched

- **WHEN** the user changes vaults
- **THEN** no file in the previous vault is created, modified, or deleted

### Requirement: Missing or unreadable vault is recoverable

When the saved vault is missing, is not a directory, or cannot be read, the application SHALL show
the welcome state with an actionable message and MUST NOT create the missing path. The saved value
SHALL remain until the user chooses another folder.

#### Scenario: Saved path no longer exists

- **WHEN** the saved vault path is missing
- **THEN** the welcome state explains the problem and offers vault selection

#### Scenario: Saved path is a file

- **WHEN** the saved vault path is a regular file
- **THEN** the welcome state explains that a vault must be a directory

#### Scenario: Missing path is not created

- **WHEN** the saved vault path is missing
- **THEN** the application does not create it

#### Scenario: Unreadable directory is reported

- **WHEN** the saved vault directory cannot be read
- **THEN** the welcome state explains the problem and offers vault selection

## ADDED Requirements

### Requirement: A vault can be supplied for a single run

The application SHALL accept a vault directory supplied at start. That directory SHALL be used for
the run, resolved to an absolute path, and validated like any other vault path. It MUST NOT replace
the vault remembered in settings. An invalid supplied path SHALL be reported and the application
SHALL exit with a non-zero status.

#### Scenario: Supplied vault opens for the run

- **WHEN** the application starts with an existing directory supplied for this run only
- **THEN** it opens that vault without asking the user to choose

#### Scenario: Remembered vault is not replaced

- **WHEN** a vault is supplied for a run and the application exits
- **THEN** the settings file still names the previously remembered vault

#### Scenario: Invalid supplied path is reported

- **WHEN** the supplied path is missing, is not a directory, or cannot be read
- **THEN** the application reports the problem and exits non-zero without opening the workspace
