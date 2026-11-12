# Spec Delta

## MODIFIED Requirements

### Requirement: A vault can be created on request

From the welcome state and from the change-vault action, the user SHALL be able to create a vault at
a path that does not exist or is an empty directory. Creation SHALL create the path and any missing
intermediate folders, seed the default folders, write the guide note, write the notes of the chosen
template when one is chosen, remember the vault, and open it. A path that exists and is not an empty
directory MUST be refused. Creation MUST stay explicit: no open, scan, or recovery step may create a
vault.

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
- **THEN** it names the default folders and the notes that will be created before anything is
  written

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
- **THEN** the template's notes are written into the new vault, the guide note is written, and the
  workspace opens

## ADDED Requirements

### Requirement: Creation offers the bundled templates

The creation action SHALL offer the bundled templates and an option to create the vault without
starter content. The no-template option SHALL be preselected on every creation, including the first
one. The choice SHALL be available in both presentations and from both the welcome state and the
change-vault action, and the vault MUST be created exactly as previewed.

#### Scenario: Blank is preselected on first launch

- **WHEN** the creation action opens with no vault previously opened
- **THEN** creating without starter content is the selected option

#### Scenario: Blank is preselected later

- **WHEN** the creation action opens while a vault is already open
- **THEN** creating without starter content is still the selected option

#### Scenario: Templates are described in the picker

- **WHEN** the picker is shown
- **THEN** every template is listed with its label and one-sentence description

#### Scenario: Preview names notes as well as folders

- **WHEN** the user chooses a template
- **THEN** the preview names the folders and how many notes will be written, and choosing no template
  previews the guide note only

#### Scenario: Choosing a template changes nothing until confirmed

- **WHEN** the user selects a template and then cancels
- **THEN** no directory, folder, or note is written and the previous screen remains

#### Scenario: Both presentations offer the same choice

- **WHEN** creation runs in a desktop window or in a browser session
- **THEN** the same templates and the same preselected option are offered

#### Scenario: Desktop shows the choice before the folder dialog

- **WHEN** the desktop user opens the creation action
- **THEN** the starter-content form is shown with a path field and a browse action, and the folder
  dialog opens only when the browse action is used

#### Scenario: Desktop browse fills the folder

- **WHEN** the desktop user chooses a folder from the form's browse action
- **THEN** the path field shows the selected folder and creation uses it
