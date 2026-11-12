# Spec Delta

## MODIFIED Requirements

### Requirement: New page type follows the project or note scheme

Creating a page from an unresolved reference SHALL derive its type and default folder from the
reference scheme: `note:` creates an uncategorized reference, `project:` creates a project, and
`log:` creates a log entry dated by the reference name. The draft SHALL open in edit mode with a
level-1 heading containing the reference name and an otherwise empty body.

#### Scenario: Note scheme creates an uncategorized reference

- **WHEN** the user creates a page from `note:Quarterly budget`
- **THEN** the draft has type `reference`, no category, and defaults to
  `reference/Quarterly budget.md`

#### Scenario: Project scheme creates a project

- **WHEN** the user creates a page from `project:Release 1.0`
- **THEN** the draft has type `project` and defaults to `projects/Release 1.0.md`

#### Scenario: Log scheme creates a log entry

- **WHEN** the user creates a page from `log:2025-10-12`
- **THEN** the draft has type `log`, date `2025-10-12`, and defaults to
  `log/2025/10/2025-10-12.md`

#### Scenario: Heading preserves the reference wording

- **WHEN** the user creates a page from `note:Q1: Planning?`
- **THEN** the draft heading reads `# Q1: Planning?` while the identity is `Q1 Planning`

### Requirement: The page edits the body and the four labels

Edit mode SHALL present the complete Markdown body, including its headings and steps, as raw text,
along with a label form for type, date, category, status, due date, and requester. Date SHALL be
offered for every note. Category SHALL be offered only for references; due date and requester only
for projects; log SHALL offer none of them. Status choices SHALL follow the selected type. An invalid
label value SHALL block the save and show an inline error.

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

#### Scenario: Log offers no workflow labels

- **WHEN** a log entry is edited
- **THEN** category, status, due date, and requester are not offered

#### Scenario: An invalid date shows a warning

- **WHEN** the Date field contains a malformed value
- **THEN** the warning from `note-model` is shown and the save is blocked until it is valid

### Requirement: The page edits the project requester

Edit mode SHALL offer an `Asked by` field for projects. The field SHALL accept one line of text.
A non-blank value SHALL be trimmed and written as `asked_by`. A blank value SHALL remove the key.
Changing the note type away from `project` SHALL remove the key before saving. The write SHALL
preserve the body, unknown keys, and every other frontmatter value.

#### Scenario: The field is offered for projects

- **WHEN** the selected type is `project`
- **THEN** the `Asked by` field is offered

#### Scenario: The field is not offered for other types

- **WHEN** the selected type is `reference`, `note`, or `log`
- **THEN** the `Asked by` field is not offered

#### Scenario: A requester is written

- **WHEN** the user enters `Priya Nair` in the field and saves
- **THEN** the frontmatter contains `asked_by: Priya Nair`

#### Scenario: Clearing removes the key

- **WHEN** the user clears the field and saves
- **THEN** the `asked_by` key is removed and every other value is kept

#### Scenario: A type change clears the requester

- **WHEN** a project with `asked_by` is changed to a reference and saved
- **THEN** the `asked_by` key is removed

#### Scenario: The rest of the note is preserved

- **WHEN** the requester is set or cleared
- **THEN** the body, unknown frontmatter keys, and the newline style are unchanged

#### Scenario: The requester is not a link

- **WHEN** the user saves a requester
- **THEN** no body reference is created or rewritten

#### Scenario: A log never carries a requester

- **WHEN** a project with `asked_by` is changed to `log`
- **THEN** the `asked_by` key is removed before the save

### Requirement: Type changes preview stranded references

Changing a note's type can move it between the `note`, `project`, and `log` schemes. For a change
between `note` and `project`, the application SHALL list inbound references that will become
unresolved and SHALL require confirmation. A change to or from `log` SHALL rewrite inbound
references automatically as defined by `note-identity` and SHALL NOT use the stranded-reference
preview. A category change MUST NOT change resolution; it only moves the file.

#### Scenario: Scheme change is previewed

- **WHEN** a note referenced as `note:Prepare report` is changed to a project
- **THEN** the confirmation lists the notes whose `note:Prepare report` references will become
  unresolved

#### Scenario: Cancel restores the type

- **WHEN** the user cancels the type change confirmation
- **THEN** the original type is kept and nothing is written

#### Scenario: Same-scheme change needs no confirmation

- **WHEN** a note changes between `note` and `reference`
- **THEN** no inbound reference is stranded and no confirmation is required

#### Scenario: References are not retargeted

- **WHEN** the scheme change is confirmed
- **THEN** inbound references keep their original destinations and are reported as unresolved

#### Scenario: A category change keeps references

- **WHEN** a reference's category changes
- **THEN** its `note:` references still resolve and only its file location may change

#### Scenario: A log conversion rewrites without a preview

- **WHEN** a reference is changed to `log`
- **THEN** inbound references are rewritten and no stranded-reference preview is shown

#### Scenario: Leaving the log rewrites without a preview

- **WHEN** a log entry is changed to `reference` or `project`
- **THEN** inbound references are rewritten and no stranded-reference preview is shown

### Requirement: Rename and trash are available from the page

The page SHALL offer Rename for notes, references, and projects, and SHALL hide it for log entries.
The page SHALL offer Trash for every type. Rename SHALL use the existing preview, confirmation,
atomic-write, and inbound-reference rules. Rename SHALL update a level-1 heading only when its text
matches the old identity. After a rename or trash, the page history SHALL be updated so Back never
returns to a path that no longer exists.

#### Scenario: Rename previews affected references

- **WHEN** the user requests a rename from the page
- **THEN** the application reports the affected note and reference counts before asking for
  confirmation

#### Scenario: Matching heading follows the identity

- **WHEN** a note's first heading text equals its old identity and the note is renamed
- **THEN** the heading is updated to the new identity

#### Scenario: Custom heading is preserved

- **WHEN** a note's first heading differs from its old identity and the note is renamed
- **THEN** the heading is unchanged

#### Scenario: Trash previews inbound references

- **WHEN** the user requests trash from the page
- **THEN** the application reports the destination and inbound references before confirmation

#### Scenario: History skips the removed path

- **WHEN** the current page is renamed or trashed
- **THEN** Back opens the previous page and never the old path

#### Scenario: A log entry has no Rename action

- **WHEN** a log entry is open
- **THEN** the page offers no Rename action

#### Scenario: A log entry can be trashed

- **WHEN** a log entry is open
- **THEN** the page offers the Trash action

## ADDED Requirements

### Requirement: Read mode shows the note date

Read mode SHALL show the note's `date` in the page meta row for every note. A project SHALL also show
its `due_date` as a separate value. A missing date SHALL show an add-date action, and a malformed
date SHALL show the warning defined by `note-model`.

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
