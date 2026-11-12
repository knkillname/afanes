# Spec Delta

## REMOVED Requirements

### Requirement: Any existing directory is a vault

**Reason**: A vault now requires an explicit on-disk schema file so future format changes can be detected and migrated safely.

**Migration**: A folder with all five default folders can be adopted through the explicit adoption flow, which writes `afanes.yaml`. Other folders must be created as new vaults or given `afanes.yaml` manually.

## ADDED Requirements

### Requirement: A versioned directory is a vault

The application SHALL accept an existing, readable directory as a vault when it contains a valid `afanes.yaml`. It MUST NOT require a specific subdirectory layout or pre-existing notes in a versioned vault. A directory without a valid settings file is not opened as a vault.

#### Scenario: Versioned empty directory is accepted

- **WHEN** an empty directory contains a valid `afanes.yaml`
- **THEN** the vault opens and the Inbox shows an empty state

#### Scenario: Notes are discovered on open

- **WHEN** a versioned vault contains notes
- **THEN** the Inbox shows the notes under its inbox directory

#### Scenario: Versioned custom layout is accepted

- **WHEN** a versioned vault stores notes outside the default folders
- **THEN** it opens and scans those notes

#### Scenario: Unversioned directory is refused

- **WHEN** a directory has no `afanes.yaml`
- **THEN** it is not opened as a vault and no file is created

#### Scenario: No marker is created on open

- **WHEN** an unversioned directory is opened
- **THEN** no marker file or directory is created

### Requirement: An unversioned vault can be adopted

When a folder without `afanes.yaml` is selected and contains all five default folders, the application SHALL offer adoption. Confirming SHALL create only `afanes.yaml` and open the folder. When a vault is already open, the current vault MUST remain open and MUST NOT be replaced until adoption is confirmed.

#### Scenario: Welcome state offers adoption

- **WHEN** the user chooses an adoptable folder and no vault is open
- **THEN** the welcome state explains the missing settings file and offers to create it

#### Scenario: A remembered adoptable folder is offered on launch

- **WHEN** the remembered folder is adoptable and has no settings file
- **THEN** the welcome state offers adoption and the folder stays unmodified

#### Scenario: Change vault offers adoption

- **WHEN** a vault is open and the user chooses an adoptable folder
- **THEN** the current vault stays open and the application offers to create the settings file

#### Scenario: Confirming adoption opens the folder

- **WHEN** the user confirms adoption
- **THEN** only `afanes.yaml` is created and the folder opens as a vault

#### Scenario: Declining adoption changes nothing

- **WHEN** the user dismisses the adoption offer
- **THEN** no settings file is written and the previous screen or vault remains

#### Scenario: Incompatible folder is not offered adoption

- **WHEN** the chosen unversioned folder is missing a default folder or is not writable
- **THEN** the application refuses it and does not offer adoption

## MODIFIED Requirements

### Requirement: A vault can be created on request

From the welcome state and from the change-vault action, the user SHALL be able to create a vault at
a path that does not exist or is an empty directory. Creation SHALL create the path and any missing
intermediate folders, write `afanes.yaml` with the current schema, seed the default folders, write
the guide and any chosen template's notes, remember the vault, and open it. A non-empty directory MUST
be refused, and no open, scan, or recovery step may create a vault.

#### Scenario: Missing path is created and opened

- **WHEN** the user creates a vault at a path that does not exist
- **THEN** the directory is created, versioned, seeded, remembered, and the workspace opens

#### Scenario: Empty directory is seeded and opened

- **WHEN** the user creates a vault at an existing empty directory
- **THEN** the directory is versioned, seeded, remembered, and the workspace opens

#### Scenario: Created vault contains the settings file

- **WHEN** a vault is created
- **THEN** `afanes.yaml` exists at its root with `schema_version: 1`

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
- **THEN** it names the default folders, the settings file, and the notes that will be created before
  anything is written

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

#### Scenario: Chosen template is written

- **WHEN** the user creates a vault and selects a template
- **THEN** the template's notes are written into the new vault, the guide note is written, the
  settings file exists, and the workspace opens

### Requirement: The user can change vaults

From the Inbox, the user SHALL be able to choose a different vault without restarting, using the
selection action available in the current presentation. The new path SHALL be persisted only after
the new vault opens, and the previous vault MUST NOT be modified. A folder without a valid settings
file is not opened until adoption is confirmed.

#### Scenario: Changing the vault

- **WHEN** the user chooses a different versioned directory through Change vault
- **THEN** the Inbox shows the new vault and the new path is saved

#### Scenario: Changing the vault in a browser session

- **WHEN** a browser session user enters the path of a different versioned directory
- **THEN** the Inbox shows the new vault and the new path is saved

#### Scenario: Changing to an adoptable folder offers adoption

- **WHEN** the user chooses an adoptable unversioned folder
- **THEN** the current vault stays open and the application offers to create the settings file

#### Scenario: Changing to an incompatible folder is refused

- **WHEN** the user chooses an unversioned folder that is not adoptable
- **THEN** the current vault stays open, the message explains why, and the saved path is unchanged

#### Scenario: Cancelling keeps the current vault

- **WHEN** the user cancels the selection during a change
- **THEN** the current vault remains active and the saved path is unchanged

#### Scenario: The previous vault is untouched

- **WHEN** the user changes vaults
- **THEN** no file in the previous vault is created, modified, or deleted

### Requirement: Missing or unreadable vault is recoverable

When the saved vault is missing, is not a directory, cannot be read, or does not contain a valid
`afanes.yaml`, the application SHALL show the welcome state with an actionable message and MUST NOT
create the missing path or settings file. The saved value SHALL remain until the user chooses another
folder or confirms adoption.

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

#### Scenario: Saved folder has no settings file

- **WHEN** the saved folder has no `afanes.yaml`
- **THEN** the welcome state explains the problem, offers adoption when the folder is adoptable, and
  writes nothing

#### Scenario: Saved folder has an unsupported schema

- **WHEN** the saved folder has an invalid or unsupported `afanes.yaml`
- **THEN** the welcome state explains the problem and leaves the file unchanged

### Requirement: A vault can be supplied for a single run

The application SHALL accept a vault directory supplied at start. That directory SHALL be used for
the run, resolved to an absolute path, and validated like any other vault path. It MUST NOT replace
the vault remembered in settings. An invalid supplied path, including a folder without a valid
settings file, SHALL be reported and the application SHALL exit with a non-zero status.

#### Scenario: Supplied vault opens for the run

- **WHEN** the application starts with an existing versioned directory supplied for this run only
- **THEN** it opens that vault without asking the user to choose

#### Scenario: Read-only versioned vault opens for the run

- **WHEN** the application starts with a read-only directory that contains a valid `afanes.yaml`
- **THEN** it opens that vault for browsing

#### Scenario: Remembered vault is not replaced

- **WHEN** a vault is supplied for a run and the application exits
- **THEN** the settings file still names the previously remembered vault

#### Scenario: Invalid supplied path is reported

- **WHEN** the supplied path is missing, is not a directory, or cannot be read
- **THEN** the application reports the problem and exits non-zero without opening the workspace

#### Scenario: Unversioned supplied folder is reported

- **WHEN** the supplied folder has no `afanes.yaml`
- **THEN** the application reports the problem, points at the adoption command, and exits non-zero
  without writing to the folder

#### Scenario: Supplied folder is not auto-adopted

- **WHEN** the supplied folder is adoptable but has no `afanes.yaml`
- **THEN** the application does not create the file and exits non-zero
