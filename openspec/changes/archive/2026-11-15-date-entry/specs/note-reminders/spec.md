# Spec Delta

## MODIFIED Requirements

### Requirement: The reminder editor sets and changes a schedule

The reminder editor SHALL be a separate surface from the page's label form. It SHALL offer the six
recurrence kinds, one or more times, and a searchable IANA zone list defaulting to the system zone.
For a project with a due date, a one-shot SHALL offer same-day, one-day-before, and one-week-before
shortcuts. Choosing a monthly day that does not exist every month SHALL show an inline warning and
suggest the last-day or last-weekday choice. Cancelling SHALL write nothing.

#### Scenario: A daily reminder is set

- **WHEN** the user chooses Daily, `09:00`, and a zone, then saves
- **THEN** the page's `reminder` mapping contains that recurrence and zone

#### Scenario: A one-shot is set

- **WHEN** the user chooses a one-shot date and time, then saves
- **THEN** the page's `reminder` mapping contains that `once` value

#### Scenario: A selected-weekday reminder is set

- **WHEN** the user chooses Monday, Wednesday, and Friday, then saves
- **THEN** the `weekdays` list contains those days

#### Scenario: The zone picker defaults to the system zone

- **WHEN** the editor opens
- **THEN** the selected zone is the computer's current IANA zone

#### Scenario: The zone picker is searchable

- **WHEN** the user types part of a zone name
- **THEN** the list filters to matching IANA zones

#### Scenario: A deadline shortcut fills a one-shot

- **WHEN** a project has a due date and the user chooses “One day before”
- **THEN** the one-shot date is the day before that due date at the chosen time

#### Scenario: A short-month warning is shown

- **WHEN** the user chooses the 31st for a monthly reminder
- **THEN** an inline warning explains that some months have no 31st and suggests the last-day choice

#### Scenario: A fifth-weekday warning is shown

- **WHEN** the user chooses the fifth Friday for a monthly reminder
- **THEN** an inline warning explains that some months have only four Fridays and suggests the last-Friday choice

#### Scenario: Cancelling writes nothing

- **WHEN** the user cancels the reminder editor
- **THEN** no file is created, changed, or removed

#### Scenario: The one-shot date offers the day-only picker

- **WHEN** the user edits the date portion of a one-shot reminder
- **THEN** the field embeds the calendar action and the shared picker offers day precision only

#### Scenario: The date picker preserves the typed time

- **WHEN** the user confirms a day from the one-shot picker
- **THEN** the one-shot date changes and the previously typed time is preserved

#### Scenario: A typed one-shot remains valid

- **WHEN** the user types a valid one-shot value into the field
- **THEN** the existing save path runs without opening the picker

#### Scenario: Cancelling the one-shot picker writes nothing

- **WHEN** the user cancels the one-shot picker
- **THEN** the one-shot field and the page are unchanged
