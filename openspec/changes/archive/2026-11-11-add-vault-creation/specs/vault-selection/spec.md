# Spec Delta

## ADDED Requirements

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
