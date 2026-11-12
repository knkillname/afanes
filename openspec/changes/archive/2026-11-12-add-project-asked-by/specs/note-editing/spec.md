# Spec Delta

## ADDED Requirements

### Requirement: The project meta row shows the requester

Read mode SHALL show `Asked by <name>` in the project meta row when the project declares
`asked_by`. The row SHALL omit the label when the key is absent. The value SHALL be displayed as
plain text and SHALL NOT add a navigation control.

#### Scenario: A project with a requester shows it

- **WHEN** a project declares `asked_by: Priya Nair`
- **THEN** the meta row shows `Asked by Priya Nair`

#### Scenario: A project without a requester omits the label

- **WHEN** a project has no `asked_by` key
- **THEN** the meta row shows no requester label

#### Scenario: Non-project pages show no requester

- **WHEN** a reference or capture is open in read mode
- **THEN** no requester label is shown

#### Scenario: Viewing the requester writes nothing

- **WHEN** the project meta row is shown
- **THEN** no note file is created, changed, or removed

### Requirement: The page edits the project requester

Edit mode SHALL offer an `Asked by` field for projects. The field SHALL accept one line of text.
A non-blank value SHALL be trimmed and written as `asked_by`. A blank value SHALL remove the key.
Changing the note type away from `project` SHALL remove the key before saving. The write SHALL
preserve the body, unknown keys, and every other frontmatter value.

#### Scenario: The field is offered for projects

- **WHEN** the selected type is `project`
- **THEN** the `Asked by` field is offered

#### Scenario: The field is not offered for other types

- **WHEN** the selected type is `reference` or `note`
- **THEN** the `Asked by` field is not offered

#### Scenario: A requester is written

- **WHEN** the user enters `Priya Nair` in the field and saves
- **THEN** the frontmatter contains `asked_by: Priya Nair`

#### Scenario: Clearing removes the key

- **WHEN** the user clears the field and saves
- **THEN** the `asked_by` key is removed and every other value is kept

#### Scenario: A type change clears the requester

- **WHEN** a project with `asked_by` is changed to a reference and saved
- **THEN** the `asked_by` key is removed

#### Scenario: The rest of the note is preserved

- **WHEN** the requester is set or cleared
- **THEN** the body, unknown frontmatter keys, and the newline style are unchanged

#### Scenario: The requester is not a link

- **WHEN** the user saves a requester
- **THEN** no body reference is created or rewritten
