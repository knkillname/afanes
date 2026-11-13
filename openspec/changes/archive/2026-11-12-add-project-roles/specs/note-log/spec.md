# Spec Delta

## MODIFIED Requirements

### Requirement: A log note is a dated entry

A note whose `type` is `log` SHALL carry an optional ISO `date`, a body, and a display title from its
first level-1 heading. It MUST NOT carry `category`, `status`, `due_date`, `asked_by`, or `owner`. A
log note without a date SHALL remain readable and SHALL appear in the Undated group rather than
being reported as a parse failure.

#### Scenario: A valid log note parses

- **WHEN** a note declares `type: log` and `date: 2025-10-12`
- **THEN** it parses as a log note with a day-precision date

#### Scenario: A log note without a date is undated

- **WHEN** a note declares `type: log` and no `date`
- **THEN** it parses and appears in the Undated group

#### Scenario: A category is rejected

- **WHEN** a log note declares `category: personal`
- **THEN** parsing reports a validation error

#### Scenario: A status is rejected

- **WHEN** a log note declares `status: archived`
- **THEN** parsing reports a validation error

#### Scenario: A due date is rejected

- **WHEN** a log note declares `due_date: 2025-10-12`
- **THEN** parsing reports a validation error

#### Scenario: A requester is rejected

- **WHEN** a log note declares `asked_by: Sam Rivera`
- **THEN** parsing reports a validation error

#### Scenario: An owner is rejected

- **WHEN** a log note declares `owner: Sam Rivera`
- **THEN** parsing reports a validation error

### Requirement: The Log search filters the tree and the calendar

The Log SHALL apply the workspace search query to both the date tree and the calendar. Matching SHALL
use the same title, identity, body, step-text, and role-name rules as the rest of the browser. Days
without a match MUST NOT be accented while a query is active.

#### Scenario: Matching entries remain in the tree

- **WHEN** the user searches for `dentist` and one log entry contains that word
- **THEN** the tree lists only the matching entry

#### Scenario: Non-matching days lose their accent

- **WHEN** a search query matches only one entry
- **THEN** only that entry's day keeps its tint and dot

#### Scenario: An empty query restores the archive

- **WHEN** the user clears the search field
- **THEN** the full tree and every entry accent return

#### Scenario: A role name match names the project

- **WHEN** the Log is in Everything mode and a project's owner, requester, or step owner matches the
  query
- **THEN** the project is listed
