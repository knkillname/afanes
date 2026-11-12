# Spec Delta

## MODIFIED Requirements

### Requirement: Creating a vault seeds the default folders

Creating a vault SHALL seed `inbox/`, `trash/`, `reference/`, and `projects/` inside the new vault.
Seeding SHALL create those folders and no files of its own. The seeded layout MUST remain a
convenience: its absence on a later open SHALL NOT be an error, and it SHALL NOT become a marker or a
validation requirement.

#### Scenario: All default folders are created

- **WHEN** a vault is created
- **THEN** all four default folders exist inside the new vault

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

## ADDED Requirements

### Requirement: A created vault contains exactly the guide and the chosen template

Vault creation SHALL write the guide note into every new vault and, when a template is chosen, the
notes that template declares. Creation MUST NOT write any other file, and applying a template MUST
NOT write outside the new vault.

#### Scenario: Blank vault holds only the guide

- **WHEN** a vault is created without a template
- **THEN** the vault contains the four default folders and the guide note, and no other file

#### Scenario: Templated vault holds the guide and the template

- **WHEN** a vault is created from a template
- **THEN** the vault contains the four default folders, the guide note, and exactly the notes the
  template declares

#### Scenario: Template notes land in their declared folders

- **WHEN** a template declares `reference/person/Ada.md` and `projects/Home.md`
- **THEN** those two files exist at those paths and no folder outside the vault is touched
