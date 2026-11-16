# Spec Delta

## MODIFIED Requirements

### Requirement: Project metadata and steps

A project outcome SHALL become `type: project` with a status and an optional due date. Its steps are checkbox items in its body. Processing SHALL preserve any task list item carried by the capture and MUST NOT create steps in another note unless the user chooses Append step. The optional due date SHALL offer the shared day-only calendar action, and its typed ISO field SHALL remain valid.

#### Scenario: Project is filed flat

- **WHEN** a capture becomes a project
- **THEN** the project note is filed directly under `projects/`

#### Scenario: Steps come from the capture body

- **WHEN** the capture body contains task list items
- **THEN** those lines become the project's steps

#### Scenario: Steps are added later

- **WHEN** the user adds a step to a project
- **THEN** a task list item is appended to the project body

#### Scenario: A project may start empty

- **WHEN** the capture body contains no task list item
- **THEN** the project is created with no steps and parses

#### Scenario: Project has no project key

- **WHEN** a project note is written
- **THEN** it does not declare a `project` key

#### Scenario: The due date offers the day-only picker

- **WHEN** a project outcome shows its optional due date field
- **THEN** the field embeds the calendar action and the shared picker offers day precision only

#### Scenario: A picked due date fills the processing field

- **WHEN** the user confirms a day from the due date picker
- **THEN** the due date field receives that ISO day and the existing preview and apply path uses it
- **AND WHEN** the user cancels the picker
- **THEN** the due date field and the capture are unchanged

#### Scenario: A typed due date remains valid

- **WHEN** the user types a valid ISO day into the due date field
- **THEN** the existing preview and apply validation runs without opening the picker
