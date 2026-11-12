# Spec Delta

## ADDED Requirements

### Requirement: Creating a vault seeds the default folders

Creating a vault SHALL seed `inbox/`, `trash/`, `reference/`, `reference/people/`, `projects/`, and
`actions/` inside the new vault. Seeding SHALL create those folders and no files. The seeded layout
MUST remain a convenience: its absence on a later open SHALL NOT be an error, and it SHALL NOT
become a marker or a validation requirement.

#### Scenario: All default folders are created

- **WHEN** a vault is created
- **THEN** all six default folders exist inside the new vault

#### Scenario: Seeding creates no files

- **WHEN** a vault is created
- **THEN** it contains no note, marker, or placeholder file

#### Scenario: Seeded layout is not required afterwards

- **WHEN** a default folder is removed from a created vault and the vault is reopened
- **THEN** it opens and scans as an ordinary vault

#### Scenario: Creating inside an empty directory seeds it

- **WHEN** an empty existing directory is chosen for a new vault
- **THEN** the default folders are created inside it

## MODIFIED Requirements

### Requirement: Layout is created lazily

Opening or scanning a vault MUST NOT create default folders. Apart from an explicit vault creation,
a folder SHALL be created only when a write needs it, and only inside the vault.

#### Scenario: Opening an empty vault creates nothing

- **WHEN** an empty directory is opened as a vault
- **THEN** no default folder is created

#### Scenario: First capture creates only the inbox

- **WHEN** the first capture is written
- **THEN** `inbox/` is created and no other default folder is created

#### Scenario: First trash creates only the trash folder

- **WHEN** the first note is sent to trash
- **THEN** `trash/` is created and no other default folder is created

#### Scenario: Scan performs no writes

- **WHEN** the vault is scanned
- **THEN** no folder or file is created or modified
