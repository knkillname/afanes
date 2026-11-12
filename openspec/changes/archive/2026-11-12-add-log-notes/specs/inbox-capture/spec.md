# Spec Delta

## MODIFIED Requirements

### Requirement: Capture writes a note into the inbox

Capturing text SHALL create a Markdown note under the vault's `inbox/` directory, creating the
directory when missing. The note SHALL declare `type: note` and today's `date` in ISO form, and MUST
NOT declare `status`. A successful capture SHALL clear the composer for the next thought.

#### Scenario: Capture creates a note

- **WHEN** the user captures `Buy milk`
- **THEN** `inbox/Buy milk.md` exists with `type: note` and today's date

#### Scenario: No status is written

- **WHEN** a captured note is created
- **THEN** its frontmatter has no `status` key

#### Scenario: Inbox directory is created on demand

- **WHEN** the vault has no `inbox/` directory and the user captures
- **THEN** the directory is created and the note is written

#### Scenario: Empty capture is rejected

- **WHEN** the captured text is empty or whitespace-only
- **THEN** no file is created and the composer reports that a thought is required

#### Scenario: Successful capture clears the composer

- **WHEN** the capture is written
- **THEN** the composer is empty and ready for another thought

#### Scenario: The capture date is today

- **WHEN** the user captures on 12 October 2025
- **THEN** the note declares `date: 2025-10-12`

### Requirement: Capture does not infer structure

Capture SHALL NOT infer a project, people, due date, or references from the text. The note SHALL
declare only `type` and the automatically assigned `date`, and SHALL remain unclassified until a
later workflow changes it.

#### Scenario: Bare names are not links

- **WHEN** the captured text contains `Ada`
- **THEN** no `person:Ada` reference is created

#### Scenario: No due date is inferred

- **WHEN** the captured text contains a date
- **THEN** the note has no `due_date` key

#### Scenario: Only the type is declared

- **WHEN** the note is created
- **THEN** `type` is the only classified key and `date` is the automatic note date
