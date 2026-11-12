# Spec Delta

## MODIFIED Requirements

### Requirement: Default storage folders hold four destinations

The application SHALL use `inbox/`, `trash/`, `reference/`, `projects/`, and `log/` as the default
storage folders for notes it creates. These folders are defaults, not requirements on an existing
vault.

#### Scenario: Capture is filed under inbox

- **WHEN** the user captures a thought
- **THEN** the note is created under `inbox/`

#### Scenario: Project is filed under projects

- **WHEN** a capture is processed into a project
- **THEN** the note is filed under `projects/`

#### Scenario: Reference is filed under reference

- **WHEN** a capture is processed into a reference
- **THEN** the note is filed under `reference/`

#### Scenario: Trash is filed under trash

- **WHEN** the user discards a note through the Trash outcome
- **THEN** the note is moved under `trash/`

#### Scenario: Log is filed under log

- **WHEN** a log entry is created for `2025-10-12`
- **THEN** it is filed under `log/2025/10/`

### Requirement: Creating a vault seeds the default folders

Creating a vault SHALL seed `inbox/`, `trash/`, `reference/`, `projects/`, and `log/` inside the new
vault. Seeding SHALL create those folders and no files of its own. The seeded layout MUST remain a
convenience: its absence on a later open SHALL NOT be an error, and it SHALL NOT become a marker or
a validation requirement.

#### Scenario: All default folders are created

- **WHEN** a vault is created
- **THEN** all five default folders exist inside the new vault

#### Scenario: Seeding creates no files

- **WHEN** the default folders are seeded during creation
- **THEN** seeding itself creates no file; the guide note and any selected template's notes are
  written by creation afterwards

#### Scenario: Seeded layout is not required afterwards

- **WHEN** a default folder is removed from a created vault and the vault is reopened
- **THEN** it opens and scans as an ordinary vault

#### Scenario: Creating inside an empty directory seeds it

- **WHEN** an empty existing directory is chosen for a new vault
- **THEN** the default folders are created inside it

#### Scenario: The log folder is seeded

- **WHEN** a vault is created
- **THEN** `log/` exists inside the new vault

### Requirement: Layout matching is case-insensitive

The application SHALL match default folder names case-insensitively and SHALL reuse an existing case
variant instead of creating a sibling directory.

#### Scenario: Existing inbox case variant is reused

- **WHEN** the vault contains `Inbox/`
- **THEN** a capture uses `Inbox/` and does not create `inbox/`

#### Scenario: Existing category case variant is reused

- **WHEN** the vault contains `reference/People/`
- **THEN** a person page uses `reference/People/`

#### Scenario: Existing trash case variant is excluded

- **WHEN** the vault contains `Trash/`
- **THEN** its notes are excluded from the catalog

#### Scenario: Existing log case variant is reused

- **WHEN** the vault contains `Log/2025/10/`
- **THEN** a log entry for that month uses `Log/2025/10/`

## ADDED Requirements

### Requirement: Log entries are filed by date

A log entry SHALL be filed at the folder selected by its date precision. A year entry SHALL live
directly under `log/<year>/`, and a month or day entry SHALL live under `log/<year>/<month>/`.
Changing a log entry's date SHALL move it to the folder the new date selects. An occupied
destination SHALL refuse the operation rather than overwrite or suffix the file. The folders SHALL be
created only when a write needs them.

#### Scenario: A year entry lives in the year folder

- **WHEN** a log entry is dated `2025`
- **THEN** its file is `log/2025/2025.md`

#### Scenario: A month entry lives in the month folder

- **WHEN** a log entry is dated `2025-10`
- **THEN** its file is `log/2025/10/2025-10.md`

#### Scenario: A day entry lives in the month folder

- **WHEN** a log entry is dated `2025-10-12`
- **THEN** its file is `log/2025/10/2025-10-12.md`

#### Scenario: A date change moves the file

- **WHEN** an entry is changed from `2025-10-12` to `2025-11-02`
- **THEN** it moves from `log/2025/10/` to `log/2025/11/`

#### Scenario: An occupied destination is refused

- **WHEN** the target date already has a log entry
- **THEN** no file is moved and the conflict is reported

#### Scenario: Opening a vault creates no log folder

- **WHEN** a vault with no `log/` folder is opened or scanned
- **THEN** the folder is not created

#### Scenario: The first log entry creates only its folders

- **WHEN** the first log entry is written
- **THEN** only the `log/<year>/` and `log/<year>/<month>/` folders needed by that entry are created
