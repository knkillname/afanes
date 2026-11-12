# Spec Delta

## MODIFIED Requirements

### Requirement: A vault can be created from the command line

`afanes vault create DIR` SHALL create a vault at the given path, seed the default folders, write the
guide note, apply `--template ID` when supplied, report the created vault, any parent folders it
created, the seeded folders, the template used, the notes written, and whether the vault was
remembered, then exit with status `0`. It SHALL remember the created vault unless `--no-remember` is
supplied. A rejected path or template MUST leave the filesystem and the preferences unchanged.

#### Scenario: Missing path is created

- **WHEN** a user creates a vault at a path that does not exist
- **THEN** the directory is created, the default folders are seeded, and the command exits `0`

#### Scenario: Empty directory is seeded

- **WHEN** a user creates a vault at an existing empty directory
- **THEN** that directory is seeded and the command exits `0`

#### Scenario: Success output names what was created

- **WHEN** creation succeeds
- **THEN** standard output names the vault path, any parent folders created, the seeded folders, the
  template used, the notes written, and whether the vault was remembered

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
- **THEN** the Personal template's notes and the guide note are written and the command exits `0`

#### Scenario: Omitted template creates a blank vault

- **WHEN** a user creates a vault without `--template`
- **THEN** only the default folders and the guide note are written

#### Scenario: Unknown template is refused

- **WHEN** a user supplies a template identifier that is not in the catalog
- **THEN** the command names the valid identifiers, creates nothing, changes no preferences, and exits
  `1`

## ADDED Requirements

### Requirement: The template catalog can be listed from the command line

`afanes vault templates` SHALL report every bundled template with its identifier, label, and
one-sentence description, then exit with status `0`. It MUST NOT require a display, MUST NOT open or
create a vault, and MUST NOT write any file.

#### Scenario: Listing reports the catalog

- **WHEN** a user runs `afanes vault templates`
- **THEN** standard output reports personal, work, and study with their labels and descriptions, and
  the command exits `0`

#### Scenario: Listing needs no vault

- **WHEN** no vault exists or is remembered
- **THEN** the listing still succeeds

#### Scenario: Listing writes nothing

- **WHEN** a user runs the listing
- **THEN** no directory, folder, note, or preference is created or modified
