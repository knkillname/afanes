# vault-layout Specification

## Purpose

Defines the default storage folders for captures, processed work, references, and deleted notes, and the rules that keep the layout portable, recoverable, and read-only until a write needs it.

## Requirements

### Requirement: Default storage folders hold four destinations

The application SHALL use `inbox/`, `trash/`, `reference/`, and `projects/` as the default storage folders for notes it creates. These folders are defaults, not requirements on an existing vault.

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

### Requirement: Category labels select reference folders

Categorized references created by the application SHALL be filed under `reference/<category-folder>/`, where the folder name is derived from the label through the cross-platform name policy. Uncategorized references SHALL be filed directly under `reference/`.

#### Scenario: A label selects the folder

- **WHEN** a reference has `category: place`
- **THEN** its default destination is `reference/place/`

#### Scenario: Uncategorized reference uses the reference root

- **WHEN** a reference has no category
- **THEN** its default destination is `reference/`

#### Scenario: Existing category folder is reused

- **WHEN** `reference/Place/` already exists
- **THEN** the application uses that folder and does not create `reference/place/`

### Requirement: Projects are flat and steps are not notes

Project notes created by the application SHALL be filed directly under `projects/`. Steps SHALL NOT be files; they live in the project body. A project's file location MUST NOT encode its steps.

#### Scenario: Project file is flat

- **WHEN** a project is created
- **THEN** it is a file directly under `projects/`

#### Scenario: Steps are not files

- **WHEN** a project has five steps
- **THEN** no step creates a file and the project remains one file

#### Scenario: Adding a step does not move the project

- **WHEN** a step is added to a project
- **THEN** the project's path is unchanged

### Requirement: Trash is excluded from the catalog

Notes under `trash/` SHALL be excluded from scans, name uniqueness, and reference resolution. Trash matching SHALL be case-insensitive. Trashed notes SHALL remain readable on disk.

#### Scenario: Trashed note is not scanned

- **WHEN** a note is moved to `trash/`
- **THEN** it is absent from the scanned note set

#### Scenario: Reference to a trashed note is unresolved

- **WHEN** a note references a note that is under `trash/`
- **THEN** the reference is reported as unresolved

#### Scenario: Trashed name can be reused

- **WHEN** a note named `Ada` is in `trash/` and a new `Ada` note is created
- **THEN** the new note is accepted without a numeric suffix

#### Scenario: Case variant of trash is excluded

- **WHEN** the vault contains `Trash/Ada.md`
- **THEN** it is excluded from the catalog

### Requirement: Layout matching is case-insensitive

The application SHALL match default folder names case-insensitively and SHALL reuse an existing case variant instead of creating a sibling directory.

#### Scenario: Existing inbox case variant is reused

- **WHEN** the vault contains `Inbox/`
- **THEN** a capture uses `Inbox/` and does not create `inbox/`

#### Scenario: Existing category case variant is reused

- **WHEN** the vault contains `reference/People/`
- **THEN** a person page uses `reference/People/`

#### Scenario: Existing trash case variant is excluded

- **WHEN** the vault contains `Trash/`
- **THEN** its notes are excluded from the catalog

### Requirement: Creating a vault seeds the default folders

Creating a vault SHALL seed `inbox/`, `trash/`, `reference/`, and `projects/` inside the new vault. Seeding SHALL create those folders and no files of its own. The seeded layout MUST remain a convenience: its absence on a later open SHALL NOT be an error, and it SHALL NOT become a marker or a validation requirement.

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

### Requirement: Layout is created lazily

Opening or scanning a vault MUST NOT create default folders. Apart from an explicit vault creation, a folder SHALL be created only when a write needs it, and only inside the vault.

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

### Requirement: No required layout

The application SHALL continue to accept notes anywhere in the vault. The default layout MUST NOT become a marker or a validation requirement.

#### Scenario: Note in a custom folder resolves

- **WHEN** a reference note with `category: person` lives in `work/Ada.md`
- **THEN** `person:Ada` resolves to it

#### Scenario: Custom vault structure opens

- **WHEN** a vault contains only custom directories
- **THEN** it opens and scans without requiring a default folder

#### Scenario: No marker is created

- **WHEN** a vault is opened
- **THEN** the application creates no marker file or directory

### Requirement: Destinations stay inside the vault

Every default destination SHALL be resolved inside the vault. A path that escapes the vault through traversal or a symlink SHALL be rejected before any write.

#### Scenario: Traversal is rejected

- **WHEN** a destination resolves outside the vault root
- **THEN** the write is rejected

#### Scenario: Symlink escape is rejected

- **WHEN** a destination passes through a symlink that resolves outside the vault
- **THEN** the write is rejected

#### Scenario: No write outside the vault

- **WHEN** a destination is rejected
- **THEN** no file is created or modified outside the vault

### Requirement: Trash naming and recovery

Moving a note to trash SHALL preserve its content and SHALL choose a unique filename when the name is already present. A trashed note MAY be restored by moving it back; automatic restore is outside this capability.

#### Scenario: Trash preserves content

- **WHEN** a note is moved to `trash/`
- **THEN** its bytes and body are unchanged

#### Scenario: Trash collision is unique

- **WHEN** `trash/Ada.md` already exists and another `Ada` is trashed
- **THEN** the second note receives a distinct trash filename

#### Scenario: Manual restore resolves references

- **WHEN** a trashed note is moved back to an active folder
- **THEN** its inbound references resolve on the next scan

### Requirement: The templates folder holds non-note content

The vault root SHALL reserve `templates/` for reference template cards. Files under it MUST NOT be scanned as notes, appear in the browser, participate in name uniqueness, or resolve as references. The folder name SHALL be matched case-insensitively. Opening or scanning a vault MUST NOT create the folder.

#### Scenario: A card is not scanned

- **WHEN** `templates/person.md` exists
- **THEN** it does not appear in the scanned note set

#### Scenario: A card name can belong to a note

- **WHEN** `templates/Ada.md` exists and a note named `Ada` is created
- **THEN** the note is accepted and the two do not collide

#### Scenario: A reference to a card name is unresolved

- **WHEN** a body links to `note:person` and only `templates/person.md` exists
- **THEN** the reference is unresolved

#### Scenario: Case variants are excluded

- **WHEN** the vault contains `Templates/person.md`
- **THEN** it is excluded from the note set

#### Scenario: Opening creates nothing

- **WHEN** a vault without `templates/` is opened or scanned
- **THEN** the folder is not created

#### Scenario: The browser does not list cards

- **WHEN** the browser groups references
- **THEN** no card appears in any group
