# Spec Delta

## MODIFIED Requirements

### Requirement: Frontmatter keys are shared and scoped

A note's recognized frontmatter keys SHALL be `type`, `category`, `status`, `due_date`, and
`asked_by`. `category` SHALL be valid only on a reference. `due_date` and `asked_by` SHALL be valid
only on a project. `asked_by` SHALL be a single non-empty string naming the person or group that
requested the project. Unknown keys SHALL be preserved.

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

## ADDED Requirements

### Requirement: The requester is a plain label

An `asked_by` value SHALL be stored and displayed as plain text. It SHALL NOT create a body
reference, resolve through a reference scheme, or participate in rename and trash previews.

#### Scenario: Asked by is not a reference

- **WHEN** a project declares `asked_by: Priya Nair`
- **THEN** no reference is extracted from the frontmatter and the value does not resolve to a page

#### Scenario: Renaming the named note leaves the value unchanged

- **WHEN** a project declares `asked_by: Priya Nair` and the note named `Priya Nair` is renamed
- **THEN** the project's `asked_by` value is unchanged and the project is not reported as an affected
  reference
