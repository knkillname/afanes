# Spec Delta

## ADDED Requirements

### Requirement: The project owner is a metadata reference

An `owner` value SHALL be one non-empty plain-text name or team. It SHALL resolve through the
`note:` catalog as a metadata reference for connections, rename, and search, but SHALL NOT create a
body reference. A missing or ambiguous value SHALL remain on the project and contribute no
connection.

#### Scenario: Owner resolves to a page

- **WHEN** a project declares `owner: Sam Rivera` and exactly one note is named `Sam Rivera`
- **THEN** that page lists the project under `Owned projects`

#### Scenario: Unknown owner stays plain text

- **WHEN** a project declares `owner: Finance team` and no note has that name
- **THEN** the value remains on the project and no page lists it under `Owned projects`

#### Scenario: Ambiguous owner contributes no connection

- **WHEN** two notes are named `Sam Rivera`
- **THEN** neither page lists the project and the value is unchanged

#### Scenario: Renaming the owner updates the value

- **WHEN** a project declares `owner: Sam Rivera` and the note named `Sam Rivera` is renamed to
  `Samantha Rivera`
- **THEN** the project's value becomes `Samantha Rivera` and the project is reported as an affected
  reference

#### Scenario: Trashing the owner leaves the value unchanged

- **WHEN** the note named `Sam Rivera` is moved to trash
- **THEN** the project keeps `owner: Sam Rivera` and the owned-project connection disappears

## MODIFIED Requirements

### Requirement: Frontmatter keys are shared and scoped

A note's recognized frontmatter keys SHALL be `type`, `date`, `category`, `status`, `due_date`,
`asked_by`, and `owner`. `date` SHALL be valid on every note. `category` SHALL be valid only on a
reference. `due_date`, `asked_by`, and `owner` SHALL be valid only on a project. A log note MUST NOT
declare `category`, `status`, `due_date`, `asked_by`, or `owner`. Unknown keys SHALL be preserved.

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

### Requirement: The requester is a plain label

An `asked_by` value SHALL be stored as one non-empty plain-text name or team. It SHALL resolve
through the `note:` catalog as a metadata reference for connections, rename, and search, but SHALL
NOT create a body reference or appear in body link syntax. A missing or ambiguous value SHALL remain
on the project and contribute no connection.

#### Scenario: Asked by is not a reference

- **WHEN** a project declares `asked_by: Priya Nair`
- **THEN** no body reference is extracted and the value resolves only as a metadata reference

#### Scenario: Renaming the named note updates the value

- **WHEN** a project declares `asked_by: Priya Nair` and the note named `Priya Nair` is renamed to
  `Priya King`
- **THEN** the project's value becomes `Priya King` and the project is reported as an affected
  reference

#### Scenario: Renaming the named note leaves the value unchanged

- **WHEN** a project declares `asked_by: Priya Nair` and the note is renamed outside the application
- **THEN** the project's value is unchanged and the reference is unresolved until the application
  repairs it

#### Scenario: A missing requester stays plain text

- **WHEN** a project declares `asked_by: Finance team` and no note has that name
- **THEN** the value remains and no page lists the project under `Requested projects`

#### Scenario: An ambiguous requester contributes no connection

- **WHEN** two notes are named `Priya Nair`
- **THEN** neither page lists the project and the value is unchanged

#### Scenario: Trashing the named note leaves the value unchanged

- **WHEN** the note named `Priya Nair` is moved to trash
- **THEN** the project keeps `asked_by: Priya Nair` and the requested-project connection disappears
