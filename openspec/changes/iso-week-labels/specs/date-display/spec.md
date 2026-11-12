# Spec Delta

## Purpose

Defines how the interface writes calendar dates alongside their ISO week, without changing what the vault stores.

## ADDED Requirements

### Requirement: Displayed dates include their ISO week

Every calendar date shown in the read-only interface SHALL be followed by its full ISO week date in parentheses, using
the form `YYYY-MM-DD (YYYY-Www)`.

#### Scenario: A project due date

- **WHEN** a project page shows the due date 20 November 2026
- **THEN** it reads `2026-11-20 (2026-W47)`

#### Scenario: A step plan date

- **WHEN** a step row shows the plan date 16 November 2026
- **THEN** it reads `2026-11-16 (2026-W47)`

#### Scenario: A step completion date

- **WHEN** a step row shows the actual date 12 November 2026
- **THEN** it reads `2026-11-12 (2026-W46)`

#### Scenario: The projects list and review cards

- **WHEN** a project due date appears in the projects list or a review card
- **THEN** the date includes the same ISO week label

#### Scenario: The processing preview

- **WHEN** the processing preview shows a due date
- **THEN** the date includes the same ISO week label

### Requirement: The label uses the ISO week-year

The week label SHALL use the ISO week-year and SHALL start weeks on Monday. The label MUST NOT use the calendar year
or a locale-defined week.

#### Scenario: A year-boundary Monday

- **WHEN** the date is 29 December 2025
- **THEN** the label is `2025-12-29 (2026-W01)`

#### Scenario: A New Year's Day in the previous week-year

- **WHEN** the date is 1 January 2021
- **THEN** the label is `2021-01-01 (2020-W53)`

#### Scenario: A mid-year date

- **WHEN** the date is 12 November 2026
- **THEN** the label is `2026-11-12 (2026-W46)`

### Requirement: Stored dates remain calendar dates

The ISO week label SHALL be presentation only. The vault SHALL continue to store `due_date`, `plan`, and `actual` as
`YYYY-MM-DD`, date inputs SHALL continue to accept and show `YYYY-MM-DD`, and template placeholders SHALL continue to
write calendar dates. A week date SHALL NOT become a valid stored value.

#### Scenario: Saving a due date

- **WHEN** the user saves a project due date of 20 November 2026
- **THEN** the file contains `due_date: 2026-11-20` and never `2026-W47`

#### Scenario: The due-date input

- **WHEN** the reader edits a project due date
- **THEN** the field still expects `YYYY-MM-DD` and offers no week-date input

#### Scenario: A template date placeholder

- **WHEN** a template containing `{{date:+7d}}` is rendered
- **THEN** the written text is a `YYYY-MM-DD` calendar date with no week label

#### Scenario: A week date in frontmatter

- **WHEN** a project declares `due_date: 2026-W47`
- **THEN** parsing reports a validation error and the label does not change the accepted format

### Requirement: The label is consistent and only shown for a real date

The same calendar date SHALL render the same label on every surface, and a surface with no date SHALL show no week
label.

#### Scenario: The same date on two surfaces

- **WHEN** 20 November 2026 appears on the page and in a review card
- **THEN** both show `2026-11-20 (2026-W47)`

#### Scenario: A project without a due date

- **WHEN** a project has no due date
- **THEN** no week label is shown for it

#### Scenario: A step without a plan date

- **WHEN** a step has no plan date
- **THEN** no week label is shown for it
