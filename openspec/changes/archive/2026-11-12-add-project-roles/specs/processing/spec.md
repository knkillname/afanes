# Spec Delta

## ADDED Requirements

### Requirement: Project outcomes accept role names

The Project and Done now outcomes SHALL accept an optional owner and an optional requester. A
non-blank value SHALL be trimmed and written as `owner` or `asked_by` in the same atomic write as the
classification. A blank value SHALL not write the key. The values MAY match no note and SHALL be
written as plain text. No other outcome SHALL accept these fields.

#### Scenario: Project writes an owner and requester

- **WHEN** the user creates a project with `Sam Rivera` as owner and `Priya Nair` as requester
- **THEN** the project contains `owner: Sam Rivera` and `asked_by: Priya Nair`

#### Scenario: Done now accepts role names

- **WHEN** the user chooses Done now with an owner and requester
- **THEN** the completed project contains both values

#### Scenario: Blank values write no role keys

- **WHEN** the user leaves a role field blank
- **THEN** the corresponding key is absent from the written project

#### Scenario: An unresolved name is accepted

- **WHEN** the user types a role name that matches no note
- **THEN** the value is written unchanged and may be created later from the project page

#### Scenario: Role fields suggest names

- **WHEN** the user types part of an existing note name in a role field
- **THEN** matching note names are offered as suggestions

#### Scenario: Non-project outcomes reject role names

- **WHEN** the selected outcome is Reference, Later, Log entry, Trash, or Append step
- **THEN** no owner or requester field is offered and no role key is written

#### Scenario: Append step does not inherit the project owner

- **WHEN** a capture is appended to a project that has an owner
- **THEN** the appended step has no owner unless the user sets one later

## MODIFIED Requirements

### Requirement: A log outcome writes no workflow labels

The Log entry outcome SHALL write only `type: log` and `date`. It MUST NOT write `category`,
`status`, `due_date`, `asked_by`, or `owner`, and it SHALL remove those keys if the capture carried
them.

#### Scenario: No status is written

- **WHEN** a capture becomes a log entry
- **THEN** the resulting note has no `status` key

#### Scenario: No due date is written

- **WHEN** a capture becomes a log entry
- **THEN** the resulting note has no `due_date` key

#### Scenario: No requester is written

- **WHEN** a capture becomes a log entry
- **THEN** the resulting note has no `asked_by` key

#### Scenario: No owner is written

- **WHEN** a capture becomes a log entry
- **THEN** the resulting note has no `owner` key
