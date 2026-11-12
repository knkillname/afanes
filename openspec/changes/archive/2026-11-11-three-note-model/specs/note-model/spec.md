# Spec Delta

## Purpose

Defines the three note types Afanes stores, the frontmatter keys they share, the statuses each type accepts, and the retired values that are now rejected.

## ADDED Requirements

### Requirement: Three note types

The note `type` value SHALL be exactly one of `note`, `reference`, or `project`. `note` means an unclarified capture, `reference` means non-actionable knowledge, and `project` means an outcome containing steps. `action` and `person` SHALL NOT be note types.

#### Scenario: Unclarified note is valid

- **WHEN** a note declares `type: note`
- **THEN** it parses as an unclarified capture

#### Scenario: Reference is valid

- **WHEN** a note declares `type: reference`
- **THEN** it parses as a reference

#### Scenario: Project is valid

- **WHEN** a note declares `type: project`
- **THEN** it parses as a project

#### Scenario: Action is rejected

- **WHEN** a note declares `type: action`
- **THEN** parsing reports a validation error

#### Scenario: Person is rejected

- **WHEN** a note declares `type: person`
- **THEN** parsing reports a validation error

### Requirement: Frontmatter keys are shared and scoped

A note's recognized frontmatter keys SHALL be `type`, `category`, `status`, and `due_date`. `category` SHALL be valid only on a reference, and `due_date` only on a project. Unknown keys SHALL be preserved.

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

### Requirement: Retired keys and values are errors

The keys `people` and `project` SHALL be validation errors. The `person` reference scheme and the `action` note type SHALL also be validation errors. There is no automatic migration.

#### Scenario: People key is rejected

- **WHEN** a note declares a `people` key
- **THEN** parsing reports a validation error

#### Scenario: Project key is rejected

- **WHEN** a note declares a `project` key
- **THEN** parsing reports a validation error

#### Scenario: Person scheme is rejected

- **WHEN** a body contains a `person:Ada` destination
- **THEN** parsing reports a validation error

### Requirement: Status vocabulary follows the type

A project SHALL accept `active`, `waiting`, `done`, `cancelled`, `archived`, and `later`. A reference SHALL accept `later`, `archived`, or no status. A note SHALL have no status. `inbox` SHALL NOT be a valid status.

#### Scenario: Project status is accepted

- **WHEN** a project declares `status: waiting`
- **THEN** the note parses

#### Scenario: Reference later is accepted

- **WHEN** a reference declares `status: later`
- **THEN** the note parses

#### Scenario: Note with a status is rejected

- **WHEN** a `type: note` declares any status
- **THEN** parsing reports a validation error

#### Scenario: Inbox is not a status

- **WHEN** a note declares `status: inbox`
- **THEN** parsing reports a validation error

### Requirement: Due dates are calendar dates

A `due_date` SHALL be written as `YYYY-MM-DD` and SHALL represent a calendar date, not an instant. A value with a time or timezone SHALL be a validation error.

#### Scenario: Calendar date is accepted

- **WHEN** a project declares `due_date: 2026-11-20`
- **THEN** the due date is the calendar date 20 November 2026

#### Scenario: Timestamp is rejected

- **WHEN** a due date includes a time or timezone
- **THEN** parsing reports a validation error
