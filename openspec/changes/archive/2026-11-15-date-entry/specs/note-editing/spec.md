# Spec Delta

## MODIFIED Requirements

### Requirement: The page edits the body and the label fields

Edit mode SHALL present the complete Markdown body, including its headings and steps, as raw text,
along with a label form for type, date, category, status, due date, requester, and owner. Date SHALL
be offered for every note. Category SHALL be offered only for references; due date, requester, and
owner only for projects; log SHALL offer none of those workflow labels. Status choices SHALL follow
the selected type. An invalid label value SHALL block the save and show an inline error.

#### Scenario: Body is raw Markdown

- **WHEN** the user edits a page
- **THEN** the body field contains the complete body, including its level-1 heading and steps

#### Scenario: Title is edited as the heading

- **WHEN** the user changes the first heading in the body
- **THEN** the display title changes after the body is saved

#### Scenario: Category is free form and limited to references

- **WHEN** the selected type is `reference`
- **THEN** the category field accepts any label
- **AND WHEN** the selected type is not `reference`
- **THEN** the category field is not offered

#### Scenario: Due date is limited to projects

- **WHEN** the selected type is `project`
- **THEN** the due date field is offered
- **AND WHEN** the selected type is not `project`
- **THEN** it is not offered

#### Scenario: Status follows the type

- **WHEN** the selected type changes so that the current status is invalid
- **THEN** the status is cleared before the change is saved

#### Scenario: Invalid due date is not written

- **WHEN** the due date field contains an invalid date
- **THEN** the save is blocked, an inline error is shown, and the note keeps its previous due date

#### Scenario: No people or project fields

- **WHEN** the edit form is shown
- **THEN** it offers no `people` or `project` label

#### Scenario: Steps are edited as body text

- **WHEN** the user edits a project
- **THEN** steps and their metadata are edited through the body field

#### Scenario: Date is offered on every note

- **WHEN** a note, reference, project, or log is edited
- **THEN** the Date field is offered

#### Scenario: Labels share the available width

- **WHEN** the page pane is wide enough for the visible label fields
- **THEN** Date is shown in the same row as the other visible labels

#### Scenario: Labels wrap on a narrow pane

- **WHEN** the page pane is too narrow for every visible label field
- **THEN** the fields wrap onto additional rows without horizontal scrolling

#### Scenario: The body fills the page pane

- **WHEN** the edit form is shown
- **THEN** the body field extends to the bottom of the available page pane
- **AND** its text starts at the top-left of the field

#### Scenario: Log offers no workflow labels

- **WHEN** a log entry is edited
- **THEN** category, status, due date, requester, and owner are not offered

#### Scenario: An invalid date shows a warning

- **WHEN** the Date field contains a malformed value
- **THEN** the warning from `note-model` is shown and the save is blocked until it is valid

#### Scenario: The Date field offers the precision-aware calendar action

- **WHEN** a note, reference, project, or log is edited
- **THEN** the Date field embeds the calendar action and the shared picker offers day, month, and year
  precision

#### Scenario: The Due date field offers the day-only calendar action

- **WHEN** a project is edited
- **THEN** the Due date field embeds the calendar action and the shared picker offers day precision
  only

#### Scenario: A picked date follows the existing save path

- **WHEN** the user confirms a Date or Due date value in the picker
- **THEN** the field runs its existing validation and save command
- **AND WHEN** the user cancels the picker
- **THEN** no label value changes

### Requirement: Step rows expose plan and owner actions

Every step row SHALL expose a calendar action and a person action. The calendar action SHALL set or
clear the step's plan date. The calendar action SHALL open the shared day-only date picker. The
person action SHALL manage the complete owner list. Both actions SHALL be present but muted at rest,
SHALL become emphasized on hover or keyboard focus, and SHALL remain reachable on touch devices.

#### Scenario: The plan date is set

- **WHEN** the user chooses a date from a step's calendar action
- **THEN** that step's `plan` is written as the chosen calendar date

#### Scenario: The plan date is cleared

- **WHEN** the user clears a step's plan date
- **THEN** the `plan` key is removed and the rest of the metadata is kept

#### Scenario: An owner is added

- **WHEN** the user adds `Sam Rivera` through a step's person action
- **THEN** `Sam Rivera` joins the step's owners and the step leaves the user's own list

#### Scenario: An owner is removed

- **WHEN** the user removes the last owner through a step's person action
- **THEN** the `owners` key is removed and the step becomes the user's own work again

#### Scenario: Multiple owners are managed

- **WHEN** the user adds, removes, and re-adds names through the person action
- **THEN** the written owner list contains exactly the names shown in the panel, in their shown order

#### Scenario: Actions are reachable without hover

- **WHEN** the pointer is not over a step row
- **THEN** both actions remain visible at reduced emphasis and remain reachable by keyboard focus and touch

#### Scenario: A failed write keeps the old metadata

- **WHEN** a plan or owner write fails
- **THEN** the page reports the failure and the step keeps its previous metadata

#### Scenario: The calendar action opens the day-only picker

- **WHEN** the user activates a step's calendar action
- **THEN** the shared picker opens with the step's plan date and day precision only

### Requirement: Project page shows status and due date

Read mode SHALL show a project meta row under the page title with its status and optional due date. The due date SHALL expose a calendar action that sets or clears it. The action SHALL be present but muted at rest and emphasized on hover or keyboard focus. The due-date field SHALL remain available in edit mode. The edit-mode due-date field SHALL offer the same day-only calendar action.

#### Scenario: The due date is shown

- **WHEN** a project declares `due_date: 2026-12-01`
- **THEN** the meta row shows that date

#### Scenario: A project without a due date offers the action

- **WHEN** a project has no due date
- **THEN** the meta row shows the add-date action and no date

#### Scenario: The due date is set from read mode

- **WHEN** the user chooses a date from the project meta row
- **THEN** the project frontmatter is written with that due date and the body is unchanged

#### Scenario: The due date is cleared

- **WHEN** the user clears the project due date
- **THEN** the `due_date` key is removed and the body is unchanged

#### Scenario: An invalid due date is rejected

- **WHEN** a due-date write would contain an invalid calendar date
- **THEN** nothing is written and the meta row reports the problem

#### Scenario: Non-project pages have no project meta row

- **WHEN** a note or reference is open in read mode
- **THEN** no project status or due-date control is shown

#### Scenario: The due date edit field offers the day-only picker

- **WHEN** a project is edited
- **THEN** the Due date field embeds the calendar action and the shared picker offers day precision
  only

#### Scenario: Read and edit modes share the due-date picker

- **WHEN** either the read-mode due-date action or the edit-mode field action opens
- **THEN** the same day-only picker opens with the current due date

### Requirement: Read mode shows the note date

Read mode SHALL show the note's `date` in the page meta row for every note. A project SHALL also show
its `due_date` as a separate value. A missing date SHALL show a calendar add-date action, and a dated
note SHALL show a calendar change-date action. The action SHALL open the shared precision-aware date
picker. A malformed date SHALL show the warning defined by `note-model`.

#### Scenario: A dated note shows its date

- **WHEN** a note declares `date: 2025-10`
- **THEN** the meta row shows `2025-10`

#### Scenario: A project shows both dates

- **WHEN** a project declares `date: 2025-10` and `due_date: 2026-01-15`
- **THEN** the meta row shows both values with distinct labels

#### Scenario: A missing date offers an action

- **WHEN** a note has no `date`
- **THEN** the meta row shows the add-date action and no date

#### Scenario: A malformed date shows a warning

- **WHEN** a note declares `date: last Tuesday`
- **THEN** the meta row reports the invalid value

#### Scenario: A dated note offers the change action

- **WHEN** a note declares a valid `date`
- **THEN** the meta row shows the change-date action

#### Scenario: The note date action opens the precision-aware picker

- **WHEN** the user activates the add-date or change-date action
- **THEN** the shared picker opens with the current date and day, month, and year precision

#### Scenario: A picked note date follows the existing save path

- **WHEN** the user confirms a date from the note date picker
- **THEN** the existing date save, rename, and move path runs
- **AND WHEN** the user cancels the picker
- **THEN** the note date and the vault are unchanged
