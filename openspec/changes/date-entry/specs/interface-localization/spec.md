# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: The native date picker follows the locale`
- TO: `### Requirement: The date picker follows the locale`

## MODIFIED Requirements

### Requirement: The date picker follows the locale

The date picker SHALL open in the active locale and SHALL use the locale's month names, weekday
labels, selected caption, mode switch, current-period action, and navigation controls. The calendar
SHALL be Monday-first in both languages. Choosing a date SHALL return the same `NoteDate` text and
precision regardless of locale; only its presentation changes.

#### Scenario: The Spanish picker renders in Spanish

- **WHEN** the date picker opens under Spanish
- **THEN** its month names, weekday names, mode switch, selected caption, current-period action, and
  navigation controls are Spanish

#### Scenario: The English picker renders in English

- **WHEN** the date picker opens under English
- **THEN** its month names, weekday names, mode switch, selected caption, current-period action, and
  navigation controls are English

#### Scenario: Both locales start on Monday

- **WHEN** the date picker opens in either locale
- **THEN** the weekday row starts with Monday and ends with Sunday

#### Scenario: The chosen date is locale independent

- **WHEN** the user chooses a date under either locale
- **THEN** the same `NoteDate` text and precision are returned

#### Scenario: The selected caption follows the locale

- **WHEN** the picker shows a day, month, or year selection
- **THEN** the caption uses the active locale's month and date wording
