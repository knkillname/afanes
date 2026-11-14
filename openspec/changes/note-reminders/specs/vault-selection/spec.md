# Spec Delta

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
- **THEN** `afanes.yaml` exists at its root with `schema_version: 2`

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

- **WHEN** the saved folder has an invalid or newer `afanes.yaml`
- **THEN** the welcome state explains the problem and leaves the file unchanged

#### Scenario: Saved folder has an older schema

- **WHEN** the saved folder has a schema `1` `afanes.yaml`
- **THEN** it opens by the older-schema rules instead of showing the welcome state

### Requirement: Opening a vault is read-only

Opening or scanning a vault SHALL NOT create or modify any vault file, except that a writable schema
`1` vault MAY be upgraded by rewriting only `afanes.yaml` after validation and before scanning. After
a vault opens, scheduled trash retention MAY delete expired managed trash entries before the
workspace is shown. The `inbox/` directory SHALL be created only by a capture.

#### Scenario: Opening does not create the inbox

- **WHEN** a vault without an `inbox/` directory is opened
- **THEN** no `inbox/` directory is created

#### Scenario: Scanning changes nothing

- **WHEN** the application scans a vault
- **THEN** no note content or modification time changes

#### Scenario: Unreadable notes are not repaired

- **WHEN** the scan finds a note it cannot parse
- **THEN** the note is left exactly as it was

#### Scenario: Opening runs trash retention

- **WHEN** a vault opens with a managed trash entry that is 30 or more days old
- **THEN** the entry may be deleted after opening validation and before the workspace is shown

#### Scenario: A failed retention still opens the vault

- **WHEN** trash retention cannot delete an expired entry
- **THEN** the vault still opens, the entry remains, and the failure is reported

#### Scenario: A writable old vault is upgraded

- **WHEN** a writable schema `1` vault opens
- **THEN** only `afanes.yaml` is rewritten to schema `2` after validation

#### Scenario: A read-only old vault is not modified

- **WHEN** a read-only schema `1` vault opens
- **THEN** no vault file is created or modified

#### Scenario: The upgrade does not touch notes

- **WHEN** a writable schema `1` vault is upgraded
- **THEN** no note, folder, guide, or card is created, changed, or removed

## ADDED Requirements

### Requirement: A writable older vault is upgraded on open

Opening a writable schema `1` vault SHALL upgrade `afanes.yaml` to schema `2` before scanning and
SHALL show a one-time notice. If the upgrade cannot be written, the vault SHALL still open for
browsing with reminders off and a persistent notice. The upgrade MUST NOT change any note.

#### Scenario: A writable old vault opens as version 2

- **WHEN** a writable schema `1` vault opens
- **THEN** it opens with reminders available and `afanes.yaml` at schema `2`

#### Scenario: The upgrade is reported once

- **WHEN** the upgrade succeeds
- **THEN** a one-time toast reports the new vault format

#### Scenario: An upgrade failure opens with reminders off

- **WHEN** the schema `1` upgrade cannot be written
- **THEN** the vault opens for browsing with reminders off and a persistent notice

#### Scenario: A current vault shows no upgrade notice

- **WHEN** a schema `2` vault opens
- **THEN** no upgrade notice is shown

### Requirement: A read-only older vault opens with reminders off

Opening a read-only schema `1` vault SHALL show the workspace for browsing with reminders disabled
and a persistent banner explaining that the vault must be writable to upgrade. It MUST NOT write any
file.

#### Scenario: A read-only old vault opens

- **WHEN** a read-only schema `1` vault is chosen
- **THEN** the workspace opens for browsing

#### Scenario: The old format is explained

- **WHEN** a read-only schema `1` vault is open
- **THEN** a persistent banner says the vault must be writable to upgrade

#### Scenario: Reminders are unavailable

- **WHEN** a read-only schema `1` vault is open
- **THEN** no reminder summary, editor, count, or card is shown

#### Scenario: No file is written

- **WHEN** a read-only schema `1` vault is open
- **THEN** no note or settings file is created or modified

#### Scenario: A later writable open upgrades

- **WHEN** the same vault becomes writable and opens again
- **THEN** it is upgraded to schema `2` and reminders become available
