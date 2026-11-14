# Spec Delta

## MODIFIED Requirements

### Requirement: A new log entry has a default date title

A new log entry SHALL start with the long date of its action in the active locale as its level-1
heading: a month name, day, and year for a day, a month name and year for a month, and a year for a
year. The heading SHALL remain editable, and the filename SHALL remain the ISO date.

#### Scenario: A day draft gets a long date title

- **WHEN** the user opens a draft for `2026-11-13` under English
- **THEN** the draft heading is `November 13, 2026`

#### Scenario: A Spanish day draft gets a long date title

- **WHEN** the user opens a draft for `2026-11-13` under Spanish
- **THEN** the draft heading is `13 de noviembre de 2026`

#### Scenario: A month draft gets a long date title

- **WHEN** the user opens a draft for `2026-11` under English
- **THEN** the draft heading is `November 2026`

#### Scenario: A Spanish month draft gets a long date title

- **WHEN** the user opens a draft for `2026-11` under Spanish
- **THEN** the draft heading is `noviembre de 2026`

#### Scenario: A year draft gets the year title

- **WHEN** the user opens a draft for `2026` under either locale
- **THEN** the draft heading is `2026`

#### Scenario: The default title is editable

- **WHEN** the user replaces the heading before the first write
- **THEN** the written entry uses the replacement heading

#### Scenario: The filename stays ISO

- **WHEN** an entry titled `13 de noviembre de 2026` is written
- **THEN** its filename is `2026-11-13.md`
