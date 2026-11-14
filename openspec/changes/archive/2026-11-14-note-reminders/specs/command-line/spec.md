# Spec Delta

## MODIFIED Requirements

### Requirement: A vault can be created from the command line

`afanes vault create DIR` SHALL create a vault at the given path, write `afanes.yaml` with the current
schema, seed the default folders, write the guide note, apply `--template ID` when supplied, and
report the vault, created parents, seeded folders, settings file, template, notes, and remembered
status, then exit `0`. It SHALL remember the vault unless `--no-remember` is supplied. A rejected path
or template MUST leave the filesystem and preferences unchanged.

#### Scenario: Missing path is created

- **WHEN** a user creates a vault at a path that does not exist
- **THEN** the directory is created, the settings file and default folders are written, and the command exits `0`

#### Scenario: Empty directory is seeded

- **WHEN** a user creates a vault at an existing empty directory
- **THEN** that directory is versioned and seeded, and the command exits `0`

#### Scenario: Created vault is versioned

- **WHEN** a vault is created from the command line
- **THEN** `afanes.yaml` exists at its root with `schema_version: 2`

#### Scenario: Success output names what was created

- **WHEN** creation succeeds
- **THEN** standard output names the vault path, any parent folders created, the seeded folders, the
  settings file, the template used, the notes written, and whether the vault was remembered

#### Scenario: Existing non-empty directory is refused

- **WHEN** a user creates a vault at a directory that already contains entries
- **THEN** the command reports that the path is not empty, creates nothing, and exits `1`

#### Scenario: File path is refused

- **WHEN** the path names an existing file
- **THEN** the command reports that a vault must be a directory and exits `1`

#### Scenario: Missing intermediate folders are created

- **WHEN** the path contains intermediate folders that do not exist
- **THEN** those folders and the vault are created, every created directory is reported, and the
  command exits `0`

#### Scenario: Created vault is remembered by default

- **WHEN** a user creates a vault without `--no-remember`
- **THEN** the next launch opens that vault as the remembered one

#### Scenario: no-remember leaves preferences unchanged

- **WHEN** a user creates a vault with `--no-remember`
- **THEN** the preferences file still names the previously remembered vault

#### Scenario: Created vault cannot be remembered

- **WHEN** the vault is created but the preferences file cannot be written
- **THEN** the command reports that the vault was created but not remembered and exits `1`

#### Scenario: Template is applied when requested

- **WHEN** a user creates a vault with `--template personal`
- **THEN** the Personal template's notes, the guide note, and the settings file are written and the
  command exits `0`

#### Scenario: Omitted template creates a blank vault

- **WHEN** a user creates a vault without `--template`
- **THEN** the settings file, default folders, template cards, and guide note are written, and no
  starter-template note is added

#### Scenario: Unknown template is refused

- **WHEN** a user supplies a template identifier that is not in the catalog
- **THEN** the command names the valid identifiers, creates nothing, changes no preferences, and exits
  `1`

### Requirement: A vault can be adopted from the command line

`afanes vault adopt DIR` SHALL write `afanes.yaml` with the current schema to an adoptable folder,
report the path, the settings file, the schema version, and whether the vault was remembered, then
exit with status `0`. It SHALL remember the adopted vault unless `--no-remember` is supplied. It MUST
NOT write notes, default folders, the guide, or template cards.

#### Scenario: Adoptable folder succeeds and is remembered

- **WHEN** a user runs `afanes vault adopt` on a writable folder with all five default folders
- **THEN** `afanes.yaml` is written with `schema_version: 2`, the vault is remembered, and the command exits `0`

#### Scenario: no-remember leaves preferences unchanged

- **WHEN** a user adopts a folder with `--no-remember`
- **THEN** the preferences file still names the previously remembered vault

#### Scenario: Success output names the settings file

- **WHEN** adoption succeeds
- **THEN** standard output names the vault path, the settings file, the schema version, and the remembered status

#### Scenario: Missing default folder is refused

- **WHEN** the folder is missing any of the five default folders
- **THEN** the command writes nothing, changes no preferences, and exits `1`

#### Scenario: Read-only folder is refused

- **WHEN** the folder cannot be written
- **THEN** the command writes nothing and exits `1`

#### Scenario: Invalid settings file is refused and preserved

- **WHEN** the folder already contains an invalid `afanes.yaml`
- **THEN** the command leaves the file unchanged, reports the problem, and exits `1`

#### Scenario: Already versioned folder is reported unchanged

- **WHEN** the folder already contains a valid `afanes.yaml`
- **THEN** the command reports that it is already a vault, changes nothing, and exits `0`

#### Scenario: Adopted vault cannot be remembered

- **WHEN** adoption writes the settings file but the preferences file cannot be written
- **THEN** the command reports that the vault was adopted but not remembered and exits `1`

#### Scenario: Adoption writes only the settings file

- **WHEN** adoption succeeds
- **THEN** no note, default folder, guide, or template card is created or modified
