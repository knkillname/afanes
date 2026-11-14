# Spec Delta

## MODIFIED Requirements

### Requirement: Frontmatter keys are shared and scoped

A note's recognized frontmatter keys SHALL be `type`, `date`, `category`, `status`, `due_date`,
`asked_by`, `owner`, and `reminder`. `date` SHALL be valid on every note. `category` SHALL be valid
only on a reference. `due_date`, `asked_by`, and `owner` SHALL be valid only on a project. A log note
MUST NOT declare `category`, `status`, `due_date`, `asked_by`, or `owner`. A null `status` or
`due_date` SHALL be treated as absent on every note type. Unknown keys SHALL be preserved.

#### Scenario: Category on a reference

- **WHEN** a reference declares `category: place`
- **THEN** the note parses

#### Scenario: Category on a project is rejected

- **WHEN** a project declares `category: place`
- **THEN** parsing reports a validation error

#### Scenario: Due date on a project

- **WHEN** a project declares `due_date: 2026-12-01`
- **THEN** the note parses with that due date

#### Scenario: Due date on a reference is rejected

- **WHEN** a reference declares `due_date: 2026-12-01`
- **THEN** parsing reports a validation error

#### Scenario: Asked by on a project

- **WHEN** a project declares `asked_by: Priya Nair`
- **THEN** the note parses with that requester

#### Scenario: Asked by on a reference is rejected

- **WHEN** a reference declares `asked_by: Priya Nair`
- **THEN** parsing reports a validation error

#### Scenario: Asked by on a capture is rejected

- **WHEN** a `type: note` declares `asked_by: Priya Nair`
- **THEN** parsing reports a validation error

#### Scenario: Empty asked by is rejected

- **WHEN** a project declares an empty or whitespace-only `asked_by`
- **THEN** parsing reports a validation error

#### Scenario: Non-string asked by is rejected

- **WHEN** a project declares a list or number as `asked_by`
- **THEN** parsing reports a validation error

#### Scenario: Project without asked by is valid

- **WHEN** a project declares no `asked_by` key
- **THEN** the note parses and has no requester

#### Scenario: Owner on a project

- **WHEN** a project declares `owner: Sam Rivera`
- **THEN** the note parses with that owner

#### Scenario: Owner on a reference is rejected

- **WHEN** a reference declares `owner: Sam Rivera`
- **THEN** parsing reports a validation error

#### Scenario: Owner on a capture is rejected

- **WHEN** a `type: note` declares `owner: Sam Rivera`
- **THEN** parsing reports a validation error

#### Scenario: Owner on a log is rejected

- **WHEN** a log declares `owner: Sam Rivera`
- **THEN** parsing reports a validation error

#### Scenario: Empty owner is rejected

- **WHEN** a project declares an empty or whitespace-only `owner`
- **THEN** parsing reports a validation error

#### Scenario: Non-string owner is rejected

- **WHEN** a project declares a list or number as `owner`
- **THEN** parsing reports a validation error

#### Scenario: Project without owner is valid

- **WHEN** a project declares no `owner` key
- **THEN** the note parses and has no owner

#### Scenario: Date on a capture

- **WHEN** a `type: note` declares `date: 2025-10-12`
- **THEN** the note parses with that date

#### Scenario: Date on a reference

- **WHEN** a reference declares `date: 2025-10`
- **THEN** the note parses with a month-precision date

#### Scenario: Date on a project

- **WHEN** a project declares `date: 2025` and `due_date: 2026-01-15`
- **THEN** the note parses with both values

#### Scenario: Date on a log

- **WHEN** a log declares `date: 2025-10-12`
- **THEN** the note parses with that date

#### Scenario: Category on a log is rejected

- **WHEN** a log declares `category: personal`
- **THEN** parsing reports a validation error

#### Scenario: Status on a log is rejected

- **WHEN** a log declares `status: archived`
- **THEN** parsing reports a validation error

#### Scenario: Null status is absent on a log

- **WHEN** a log declares `status: null`
- **THEN** the note parses with no status

#### Scenario: Null due date is absent on a reference

- **WHEN** a reference declares `due_date: null`
- **THEN** the note parses with no due date

## ADDED Requirements

### Requirement: A reminder key is valid only on eligible notes

A `reminder` key SHALL be valid on a reference, project, or log entry. A capture MUST NOT have an
effective reminder; one declared on a capture SHALL be ignored with a warning and preserved. A null
`reminder` SHALL be treated as absent.

#### Scenario: A reference, project, or log accepts a reminder

- **WHEN** a reference, project, or log declares a valid `reminder`
- **THEN** the key is recognized and the note parses

#### Scenario: A capture's reminder is ignored

- **WHEN** a `type: note` declares a `reminder`
- **THEN** the note parses, the reminder is ignored for scheduling, and a warning is shown

#### Scenario: A null reminder is absent

- **WHEN** an eligible note declares `reminder: null`
- **THEN** the note parses with no reminder
