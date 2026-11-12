# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Creating a vault seeds the default folders

Creating a vault SHALL seed `inbox/`, `trash/`, `reference/`, and `projects/` inside the new vault. Seeding SHALL create those folders and no files. The seeded layout MUST remain a convenience: its absence on a later open SHALL NOT be an error, and it SHALL NOT become a marker or a validation requirement.

#### Scenario: All default folders are created

- **WHEN** a vault is created
- **THEN** all four default folders exist inside the new vault

#### Scenario: Seeding creates no files

- **WHEN** a vault is created
- **THEN** it contains no note, marker, or placeholder file

#### Scenario: Seeded layout is not required afterwards

- **WHEN** a default folder is removed from a created vault and the vault is reopened
- **THEN** it opens and scans as an ordinary vault

#### Scenario: Creating inside an empty directory seeds it

- **WHEN** an empty existing directory is chosen for a new vault
- **THEN** the default folders are created inside it

## REMOVED Requirements

### Requirement: Projects and actions are flat

**Reason**: There are no action notes, and steps are not files. Only projects remain flat.

**Migration**: Move each action note into its project's body as a task list item.

### Requirement: Default storage folders

**Reason**: The folder set drops `actions/`. It is restated under the new four-destination requirement.

**Migration**: Existing `actions/` notes must be converted by hand into project steps.

### Requirement: Category folders live under reference

**Reason**: The fixed `person` to `people` mapping is replaced by a general label-to-folder mapping. It is restated under the new category-folder requirement.

**Migration**: None. Existing `reference/people/` files stay where they are.
