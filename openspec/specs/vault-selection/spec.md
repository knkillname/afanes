# vault-selection Specification

## Purpose

Defines how Afanes chooses a vault folder, remembers it between launches, changes it, and recovers when the saved location is missing or unreadable.

## Requirements

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

### Requirement: A vault can be created on request

From the welcome state and from the change-vault action, the user SHALL be able to create a vault at
a path that does not exist or is an empty directory. Creation SHALL create the path and any missing
intermediate folders, seed the default folders, remember the vault, and open it. A path that exists
and is not an empty directory MUST be refused. Creation MUST stay explicit: no open, scan, or
recovery step may create a vault.

#### Scenario: Missing path is created and opened

- **WHEN** the user creates a vault at a path that does not exist
- **THEN** the directory is created, seeded, remembered, and the workspace opens

#### Scenario: Empty directory is seeded and opened

- **WHEN** the user creates a vault at an existing empty directory
- **THEN** the directory is seeded, remembered, and the workspace opens

#### Scenario: Non-empty directory is refused

- **WHEN** the chosen path already contains entries
- **THEN** the creation action explains that the folder is not empty, nothing is written, and the
  current screen remains

#### Scenario: File path is refused

- **WHEN** the chosen path names an existing file
- **THEN** the creation action explains that a vault must be a directory and nothing is written

#### Scenario: Missing intermediate folders are created

- **WHEN** the chosen path contains intermediate folders that do not exist
- **THEN** those folders and the vault are created, and the created folders are named

#### Scenario: Browser creation names what it will write

- **WHEN** a browser session user opens the creation action
- **THEN** it names the default folders that will be created before anything is written

#### Scenario: Cancelling creation writes nothing

- **WHEN** the user dismisses the creation action without confirming
- **THEN** no directory is created, preferences are unchanged, and the previous screen remains

#### Scenario: Change vault offers both choices

- **WHEN** the user opens the change-vault action while a vault is open
- **THEN** it offers opening an existing folder and creating a new vault

#### Scenario: Second vault is created while one is open

- **WHEN** the user creates a vault while another vault is open
- **THEN** the new vault is created, remembered, and shown, and the previous vault is unmodified

#### Scenario: Created vault is remembered

- **WHEN** a vault is created
- **THEN** the next launch opens it without showing the welcome state

#### Scenario: Creation succeeds but preferences cannot be saved

- **WHEN** the vault is created and the preferences file cannot be written
- **THEN** the workspace opens in the created vault and the message says it will not be remembered

#### Scenario: Browser session creates a vault

- **WHEN** a browser session user enters the path of a new vault
- **THEN** the vault is created and the workspace opens in that session

#### Scenario: Desktop creation uses the directory dialog

- **WHEN** the desktop user creates a vault
- **THEN** the native directory dialog selects the folder, using its own new-folder action when needed,
  and the selected folder is seeded

#### Scenario: Partial creation is reported

- **WHEN** seeding fails after some folders were created
- **THEN** the failure names the folder that failed and the folders already created are left in place

#### Scenario: Opening still creates nothing

- **WHEN** a vault is opened or scanned, including a remembered path that no longer exists
- **THEN** no directory or file is created

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
