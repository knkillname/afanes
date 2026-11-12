# Spec Delta

## REMOVED Requirements

### Requirement: Three note types

**Reason**: A fourth note type, `log`, is introduced for dated diary entries.

**Migration**: None before 1.0.0. Existing notes keep their current type and no automatic migration
is provided.

## MODIFIED Requirements

### Requirement: Frontmatter keys are shared and scoped

A note's recognized frontmatter keys SHALL be `type`, `date`, `category`, `status`, `due_date`, and
`asked_by`. `date` SHALL be valid on every note. `category` SHALL be valid only on a reference.
`due_date` and `asked_by` SHALL be valid only on a project. A log note MUST NOT declare `category`,
`status`, `due_date`, or `asked_by`. Unknown keys SHALL be preserved.

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

### Requirement: Status vocabulary follows the type

A project SHALL accept `active`, `waiting`, `done`, `cancelled`, `archived`, and `later`. A reference
SHALL accept `later`, `archived`, or no status. A note and a log SHALL have no status. `inbox` SHALL
NOT be a valid status.

#### Scenario: Project status is accepted

- **WHEN** a project declares `status: waiting`
- **THEN** the note parses

#### Scenario: Reference later is accepted

- **WHEN** a reference declares `status: later`
- **THEN** the note parses

#### Scenario: Note with a status is rejected

- **WHEN** a `type: note` declares any status
- **THEN** parsing reports a validation error

#### Scenario: Log with a status is rejected

- **WHEN** a `type: log` declares any status
- **THEN** parsing reports a validation error

#### Scenario: Inbox is not a status

- **WHEN** a note declares `status: inbox`
- **THEN** parsing reports a validation error

## ADDED Requirements

### Requirement: Four note types

The note `type` value SHALL be exactly one of `note`, `reference`, `project`, or `log`. `note` means
an unclarified capture, `reference` means non-actionable knowledge, `project` means an outcome
containing steps, and `log` means a dated diary entry. `action` and `person` SHALL NOT be note types.

#### Scenario: Unclarified note is valid

- **WHEN** a note declares `type: note`
- **THEN** it parses as an unclarified capture

#### Scenario: Reference is valid

- **WHEN** a note declares `type: reference`
- **THEN** it parses as a reference

#### Scenario: Project is valid

- **WHEN** a note declares `type: project`
- **THEN** it parses as a project

#### Scenario: Log is valid

- **WHEN** a note declares `type: log`
- **THEN** it parses as a log entry

#### Scenario: Action is rejected

- **WHEN** a note declares `type: action`
- **THEN** parsing reports a validation error

#### Scenario: Person is rejected

- **WHEN** a note declares `type: person`
- **THEN** parsing reports a validation error

### Requirement: The note date is an ISO partial date

A `date` SHALL be written as `YYYY`, `YYYY-MM`, or `YYYY-MM-DD`. The number of parts SHALL determine
its precision: year, month, or day. The value SHALL be a valid calendar value at that precision and
MUST NOT contain a time or timezone. `date` SHALL be independent of a project's `due_date`.

#### Scenario: Year precision is accepted

- **WHEN** a note declares `date: 2025`
- **THEN** the note has a year-precision date

#### Scenario: Month precision is accepted

- **WHEN** a note declares `date: 2025-10`
- **THEN** the note has a month-precision date

#### Scenario: Day precision is accepted

- **WHEN** a note declares `date: 2025-10-12`
- **THEN** the note has a day-precision date

#### Scenario: A timestamp is not accepted as a date

- **WHEN** a note declares `date: 2025-10-12T09:30:00`
- **THEN** the value is treated as malformed rather than as a day-precision date

#### Scenario: A date and a due date are independent

- **WHEN** a project declares `date: 2025` and `due_date: 2026-01-15`
- **THEN** both values are preserved independently

### Requirement: A malformed date does not hide the note

An invalid `date` value SHALL NOT make the note unreadable. The note SHALL remain visible in its
browser group and SHALL appear in Undated. The page editor SHALL show a warning, and the file SHALL
NOT be rewritten until the user saves a valid value.

#### Scenario: A hand-written bad value stays visible

- **WHEN** a note declares `date: last Tuesday`
- **THEN** the note remains in its browser group and appears in Undated

#### Scenario: The editor reports the problem

- **WHEN** the page with the bad value opens in edit mode
- **THEN** the Date field shows the warning “Use 2025, 2025-10, or 2025-10-12”

#### Scenario: A valid save repairs the date

- **WHEN** the user replaces the bad value with `2025-10-12` and saves
- **THEN** the note carries the valid date and moves to its date level

#### Scenario: Scanning writes nothing

- **WHEN** a vault containing a malformed date is opened or scanned
- **THEN** the file is not rewritten
