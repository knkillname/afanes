# Spec Delta

## ADDED Requirements

### Requirement: Read mode shows the reminder summary

Read mode SHALL show a reminder summary for an eligible note that has a reminder, including its
cadence, times, stored zone, and paused state. A note without a reminder SHALL show a Set Reminder
action. A capture, a raw-rescue page, and a trashed page SHALL show no reminder editing action.
Showing the summary MUST NOT write to the vault.

#### Scenario: A reminder summary shows the schedule

- **WHEN** a page has a daily reminder at `09:00` in `America/Mexico_City`
- **THEN** read mode shows the cadence, time, and zone

#### Scenario: A page without a reminder offers the action

- **WHEN** an eligible note has no reminder
- **THEN** read mode shows a Set Reminder action

#### Scenario: A paused reminder is labeled

- **WHEN** a page's reminder is paused by status or Trash
- **THEN** the summary reports that it is paused

#### Scenario: A capture has no reminder action

- **WHEN** a note of type `note` is open
- **THEN** no reminder summary or edit action is shown

#### Scenario: A raw-rescue page has no reminder action

- **WHEN** an unparseable note is open in raw rescue mode
- **THEN** no reminder summary or edit action is shown

#### Scenario: A trashed page has no reminder edit action

- **WHEN** a trashed note is open
- **THEN** its reminder summary is visible but no edit action is shown

#### Scenario: Showing the summary writes nothing

- **WHEN** read mode renders the reminder summary
- **THEN** no note file is created, changed, or removed

### Requirement: The reminder editor is separate from the label form

The reminder SHALL be set and changed in a separate dialog or panel, not in the page label form. The
editor SHALL offer the six recurrence kinds, one or more times, a searchable IANA zone list
defaulting to the system zone, one-shot deadline shortcuts for a project with a due date, and an
inline warning for a monthly day that does not exist every month. Cancelling SHALL write nothing.

#### Scenario: The reminder action opens the editor

- **WHEN** the user chooses Set Reminder or Edit Reminder
- **THEN** the separate reminder editor opens

#### Scenario: The label form has no reminder fields

- **WHEN** the page is in edit mode
- **THEN** its label form still contains only the existing note labels

#### Scenario: Every recurrence kind is offered

- **WHEN** the editor opens
- **THEN** Daily, Selected Weekdays, Day of Month, Nth Weekday, Last Day, and Last Weekday are offered

#### Scenario: Times can be added and removed

- **WHEN** the user adds or removes a time in the editor
- **THEN** the list shows the current times and saves at least one time

#### Scenario: The zone picker defaults to the system zone

- **WHEN** the editor opens
- **THEN** the selected zone is the computer's current IANA zone

#### Scenario: The zone picker is searchable

- **WHEN** the user types part of a zone name
- **THEN** the list filters to matching IANA zones

#### Scenario: A deadline shortcut fills a one-shot

- **WHEN** a project has a due date and the user chooses One Day Before
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

### Requirement: A reminder edit uses the page write guard

Saving a reminder SHALL use the open page draft and its conflict guard. A clean page SHALL write
immediately; a dirty draft SHALL include the reminder in its next write. An external edit SHALL stop
the write and offer the existing conflict choices. A new page SHALL be created on its first save.

#### Scenario: A read-mode save writes immediately

- **WHEN** the user saves a reminder from read mode on a clean page
- **THEN** the page frontmatter is written immediately

#### Scenario: A dirty draft includes the reminder

- **WHEN** the page has unsaved body edits and the user saves a reminder
- **THEN** the next write contains the body edits and the reminder

#### Scenario: An external edit stops the write

- **WHEN** the file changes on disk before the reminder is saved
- **THEN** nothing is written and the existing conflict choices are offered

#### Scenario: A new page is created on save

- **WHEN** the user sets a reminder on a new page draft
- **THEN** the page is created with its body and reminder on the first save

#### Scenario: A failed write keeps the editor open

- **WHEN** the reminder write fails
- **THEN** the editor or draft remains and the failure is reported

### Requirement: Removing a reminder offers Undo

Removing a reminder SHALL take effect immediately and SHALL offer Undo in a toast. Undo SHALL
restore the exact previous schedule, zone, and handled occurrence. The opportunity SHALL end when
the toast is dismissed or replaced, or when the application exits.

#### Scenario: Remove clears the reminder

- **WHEN** the user chooses Remove Reminder
- **THEN** the `reminder` key is removed and a toast offers Undo

#### Scenario: Undo restores the reminder

- **WHEN** the user chooses Undo before the toast ends
- **THEN** the exact previous reminder is written back

#### Scenario: The opportunity is transient

- **WHEN** the reminder toast is dismissed or replaced
- **THEN** Undo is no longer offered

#### Scenario: A failed removal writes nothing

- **WHEN** removing the reminder cannot be written
- **THEN** the reminder remains and the failure is reported
