# vault-selection Specification

## Purpose

Defines how Afanes chooses a vault folder, remembers it between launches, changes it, and recovers when the saved location is missing or unreadable.

## Requirements

### Requirement: First launch requests a vault

On first launch, when no saved vault is available, the application SHALL present a welcome state explaining that a vault is a folder of Markdown files and offering a directory picker. It MUST NOT create or modify any vault file before a vault is chosen.

#### Scenario: Welcome appears without settings

- **WHEN** the application starts and no settings file exists
- **THEN** it shows the welcome state and does not scan or write to any vault

#### Scenario: Choosing a folder opens it

- **WHEN** the user selects an existing directory
- **THEN** the application saves that directory as the vault and shows the Inbox

#### Scenario: Cancelling leaves the welcome state

- **WHEN** the user dismisses the picker without choosing a directory
- **THEN** the welcome state remains and no settings file is written

### Requirement: Any existing directory is a vault

The application SHALL accept any existing, readable directory as a vault, including an empty one. It MUST NOT require a marker file, a specific subdirectory layout, or pre-existing notes.

#### Scenario: Empty directory is accepted

- **WHEN** the user selects an empty directory
- **THEN** the vault opens and the Inbox shows an empty state

#### Scenario: Notes are discovered on open

- **WHEN** the selected directory contains notes
- **THEN** the Inbox shows the notes under its `inbox/` directory

#### Scenario: No marker is created

- **WHEN** an empty directory is opened
- **THEN** the application creates no marker file or directory in it

### Requirement: The chosen vault is remembered

The application SHALL persist the selected vault outside the vault and SHALL reopen it on later launches without asking again. The settings file MUST NOT contain note content, and it SHALL be written atomically so a failed write leaves the previous settings intact.

#### Scenario: Later launch reopens the vault

- **WHEN** the application starts and the saved vault is readable
- **THEN** it opens that vault directly without showing the welcome state

#### Scenario: Settings live outside the vault

- **WHEN** the vault is selected
- **THEN** the settings file is created outside the vault and contains no note content

#### Scenario: Failed write preserves previous settings

- **WHEN** saving the settings fails partway through
- **THEN** the previous settings file remains readable and unchanged

### Requirement: The user can change vaults

From the Inbox, the user SHALL be able to choose a different vault without restarting. The new path SHALL be persisted, and the previous vault MUST NOT be modified.

#### Scenario: Changing the vault

- **WHEN** the user chooses a different directory through Change vault
- **THEN** the Inbox shows the new vault and the new path is saved

#### Scenario: Cancelling keeps the current vault

- **WHEN** the user dismisses the picker during a change
- **THEN** the current vault remains active and the saved path is unchanged

#### Scenario: The previous vault is untouched

- **WHEN** the user changes vaults
- **THEN** no file in the previous vault is created, modified, or deleted

### Requirement: Missing or unreadable vault is recoverable

When the saved vault is missing, is not a directory, or cannot be read, the application SHALL show the welcome state with an actionable message and MUST NOT create the missing path. The saved value SHALL remain until the user chooses another folder.

#### Scenario: Saved path no longer exists

- **WHEN** the saved vault path is missing
- **THEN** the welcome state explains the problem and offers the folder picker

#### Scenario: Saved path is a file

- **WHEN** the saved vault path is a regular file
- **THEN** the welcome state explains that a vault must be a directory

#### Scenario: Missing path is not created

- **WHEN** the saved vault path is missing
- **THEN** the application does not create it

#### Scenario: Unreadable directory is reported

- **WHEN** the saved vault directory cannot be read
- **THEN** the welcome state explains the problem and offers the folder picker

### Requirement: Corrupt settings are not overwritten silently

When the settings file is unreadable or malformed, the application SHALL start in the welcome state and report that saved preferences could not be read. It MUST NOT overwrite the file until the user chooses a vault.

#### Scenario: Malformed settings show the welcome state

- **WHEN** the settings file contains invalid data
- **THEN** the welcome state appears with a message that preferences could not be read

#### Scenario: Startup does not rewrite the file

- **WHEN** the settings file is malformed and the user does not choose a vault
- **THEN** the file remains unchanged

#### Scenario: Choosing a vault replaces unreadable settings

- **WHEN** the user chooses a vault after a malformed settings file
- **THEN** new settings are written and the application proceeds

### Requirement: Opening a vault is read-only

Opening or scanning a vault SHALL NOT create, modify, or delete any vault file. The `inbox/` directory SHALL be created only by a capture.

#### Scenario: Opening does not create the inbox

- **WHEN** a vault without an `inbox/` directory is opened
- **THEN** no `inbox/` directory is created

#### Scenario: Scanning changes nothing

- **WHEN** the application scans a vault
- **THEN** no note content or modification time changes

#### Scenario: Unreadable notes are not repaired

- **WHEN** the scan finds a note it cannot parse
- **THEN** the note is left exactly as it was

### Requirement: The vault path is stable across launches

The application SHALL resolve the selected directory to an absolute path before saving it, so launching from a different working directory opens the same vault.

#### Scenario: Launch from another directory

- **WHEN** the application is started from a different working directory
- **THEN** it opens the same vault

#### Scenario: Relative path is resolved

- **WHEN** a relative vault path is supplied
- **THEN** it is resolved to an absolute path before being saved
