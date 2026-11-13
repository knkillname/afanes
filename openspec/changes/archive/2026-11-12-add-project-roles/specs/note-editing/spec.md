# Spec Delta

## ADDED Requirements

### Requirement: The page edits the project owner

Edit mode SHALL offer an `Owner` field for projects. The field SHALL accept one line of text. A
non-blank value SHALL be trimmed and written as `owner`. A blank value SHALL remove the key.
Changing the note type away from `project` SHALL remove the key before saving. The write SHALL
preserve the body, unknown keys, and every other frontmatter value.

#### Scenario: The field is offered for projects

- **WHEN** the selected type is `project`
- **THEN** the `Owner` field is offered

#### Scenario: The field is not offered for other types

- **WHEN** the selected type is `reference`, `note`, or `log`
- **THEN** the `Owner` field is not offered

#### Scenario: An owner is written

- **WHEN** the user enters `Sam Rivera` in the field and saves
- **THEN** the frontmatter contains `owner: Sam Rivera`

#### Scenario: Clearing removes the key

- **WHEN** the user clears the field and saves
- **THEN** the `owner` key is removed and every other value is kept

#### Scenario: A type change clears the owner

- **WHEN** a project with `owner` is changed to a reference and saved
- **THEN** the `owner` key is removed

#### Scenario: The rest of the note is preserved

- **WHEN** the owner is set or cleared
- **THEN** the body, unknown frontmatter keys, and the newline style are unchanged

#### Scenario: A log never carries an owner

- **WHEN** a project with `owner` is changed to `log`
- **THEN** the `owner` key is removed before the save

### Requirement: Role name fields suggest vault names

The `Owner` and `Asked by` fields SHALL suggest matching `note:` names while the user types.
Selecting a suggestion SHALL fill the field with that name. Free text that matches no note SHALL
remain valid so a new person or team can be recorded before its note exists.

#### Scenario: Existing names are suggested

- **WHEN** the vault contains a note named `Sam Rivera` and the user types `Sam` in the Owner field
- **THEN** `Sam Rivera` is offered as a suggestion

#### Scenario: Typing filters the suggestions

- **WHEN** the user types part of a name
- **THEN** only the matching names are offered

#### Scenario: Free text is accepted

- **WHEN** the user types a name that matches no note and saves
- **THEN** the value is written unchanged as a broken role name

#### Scenario: No matches leaves no suggestions

- **WHEN** the user types a name that matches no note
- **THEN** no suggestion is shown and the field still accepts the text

### Requirement: Role names navigate from read mode

A project role name shown in read mode SHALL act as a navigation control. A resolved name SHALL open
its page. An ambiguous name SHALL show every candidate and SHALL NOT choose one. A missing name SHALL
start the missing-role-name creation flow. A role name is not a body link and SHALL NOT change the
body navigation rules.

#### Scenario: A resolved role name opens its page

- **WHEN** the user selects `Sam Rivera` in the project meta row and exactly one note is named
  `Sam Rivera`
- **THEN** that note opens

#### Scenario: An ambiguous role name asks

- **WHEN** two notes are named `Sam Rivera`
- **THEN** the page lists both candidates and opens neither until one is chosen

#### Scenario: A missing role name starts creation

- **WHEN** the user selects `Sam Rivera` and no note has that name
- **THEN** the missing-role-name creation flow starts

#### Scenario: Viewing role names writes nothing

- **WHEN** a role name is shown or selected in read mode
- **THEN** no note file is created, changed, or removed until the user confirms creation

### Requirement: A missing role name creates a categorized reference

The missing-role-name flow SHALL ask for a category in an editable combobox. Suggestions SHALL always
include `person`, every category used by a reference note, and every category offered by a valid
reference template card. A free-typed label and no category SHALL remain available, and suggestions
SHALL ignore the browser query and active section. Confirming SHALL create the reference atomically
under the chosen category and open it in edit mode; cancelling SHALL write nothing.

#### Scenario: Person is always suggested

- **WHEN** the vault has no reference with `category: person`
- **THEN** `person` is offered in the category suggestions

#### Scenario: Template categories are suggested

- **WHEN** the vault contains a valid reference template card with `category: team`
- **THEN** `team` is offered even when no reference uses it yet

#### Scenario: Search does not hide categories

- **WHEN** the browser search query matches no note in an existing category
- **THEN** that category is still offered

#### Scenario: A category is chosen

- **WHEN** the user chooses the `person` category for `Sam Rivera`
- **THEN** a reference named `Sam Rivera` is created under `reference/person/` and opens

#### Scenario: No category is chosen

- **WHEN** the user chooses no category for `Sam Rivera`
- **THEN** an uncategorized reference named `Sam Rivera` is created under `reference/` and opens

#### Scenario: A new category is typed

- **WHEN** the user types a category that is not in the suggestions
- **THEN** the new reference uses that category and its folder

#### Scenario: Creating and opening are one action

- **WHEN** the user confirms the category choice
- **THEN** the note is written immediately and opens in edit mode; no draft save step is required

#### Scenario: The new reference stays responsive

- **WHEN** the created role reference is open in edit mode
- **THEN** choosing **Done** returns to read mode
- **AND** the Back action remains available and returns to the previous page

#### Scenario: Cancelling writes nothing

- **WHEN** the user cancels the category choice
- **THEN** no note is created, changed, or removed

#### Scenario: A collision is reported

- **WHEN** the role name already belongs to a note in the `note:` scheme
- **THEN** no second note is created without an explicit resolution

### Requirement: A role reference uses the matching template

When a valid reference template card exists for the chosen category, the created role reference SHALL
include that card's starter body below the role-name heading. When no card matches, the note SHALL
contain only the heading.

#### Scenario: The matching card supplies the body

- **WHEN** the vault has a valid `person` card and the user chooses `person`
- **THEN** the new reference contains the card's `## Contact` body below `# Sam Rivera`

#### Scenario: No card leaves only the heading

- **WHEN** the chosen category has no matching template card
- **THEN** the new reference contains the role-name heading and no starter body

### Requirement: Read mode sets the project roles

Read mode SHALL offer an owner action and a requester action for projects. Each action SHALL ask for a
name with vault-name suggestions, accept a new name, and write it immediately without entering edit
mode. Each action SHALL also offer clearing the role. Cancelling SHALL write nothing, and a successful
change SHALL refresh the page, its role links, and its Connections.

#### Scenario: The owner action writes a name

- **WHEN** the reader selects the owner action, types `Sam Rivera`, and confirms
- **THEN** the project frontmatter contains `owner: Sam Rivera` without entering edit mode

#### Scenario: The requester action writes a name

- **WHEN** the reader selects the requester action, types `Priya Nair`, and confirms
- **THEN** the project frontmatter contains `asked_by: Priya Nair` without entering edit mode

#### Scenario: A typed name that matches no note is still written

- **WHEN** the reader types `Min` in the requester action without choosing a suggested note, and confirms
- **THEN** `asked_by: Min` is written and the page shows `Min` as a broken role link

#### Scenario: A role is cleared

- **WHEN** the reader selects the clear action in the owner or requester dialog
- **THEN** the corresponding key is removed and the page refreshes

#### Scenario: Cancelling writes nothing

- **WHEN** the reader cancels the owner or requester dialog
- **THEN** no file is created, changed, or removed

#### Scenario: The actions are project-only

- **WHEN** a reference, capture, or log entry is open in read mode
- **THEN** neither role action is shown

### Requirement: Step owner names navigate as role names

Every step owner name shown in read mode SHALL follow the role-name navigation rules, including the
owner panel chips and the step detail line. Selecting a name SHALL NOT remove it from the step; the
chip's delete action SHALL remain a separate control.

#### Scenario: A step owner name opens its page

- **WHEN** a step declares `owners: [Sam Rivera]` and exactly one note is named `Sam Rivera`
- **THEN** selecting the name opens that note

#### Scenario: A missing step owner name starts creation

- **WHEN** a step declares `owners: [Sam Rivera]` and no note has that name
- **THEN** selecting the name starts the missing-role-name creation flow

#### Scenario: Deleting a chip still removes the owner

- **WHEN** the user activates the chip's delete action
- **THEN** the owner is removed from the step and no page is opened

## MODIFIED Requirements

### Requirement: The page edits the body and the four labels

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

### Requirement: The project meta row shows the requester

Read mode SHALL show `Owner <name>` and `Asked by <name>` in the project meta row when the project
declares `owner` or `asked_by`, in that order. The row SHALL omit each label when its key is absent.
Each name SHALL be a navigation control that follows the role-name navigation rules. The file values
SHALL remain plain text.

#### Scenario: A project with a requester shows it

- **WHEN** a project declares `asked_by: Priya Nair`
- **THEN** the meta row shows `Asked by Priya Nair`

#### Scenario: A project without a requester omits the label

- **WHEN** a project has no `asked_by` key
- **THEN** the meta row shows no requester label

#### Scenario: Non-project pages show no requester

- **WHEN** a reference or capture is open in read mode
- **THEN** no requester label is shown

#### Scenario: Viewing the requester writes nothing

- **WHEN** the project meta row is shown
- **THEN** no note file is created, changed, or removed

#### Scenario: A project with an owner shows it

- **WHEN** a project declares `owner: Sam Rivera`
- **THEN** the meta row shows `Owner Sam Rivera`

#### Scenario: Owner is shown before requester

- **WHEN** a project declares both `owner` and `asked_by`
- **THEN** the meta row shows the owner before the requester

#### Scenario: A project without an owner omits the label

- **WHEN** a project has no `owner` key
- **THEN** the meta row shows no owner label

#### Scenario: A resolved role name opens its page

- **WHEN** the user selects a role name that resolves to exactly one note
- **THEN** that note opens

#### Scenario: A missing role name starts creation

- **WHEN** the user selects a role name that matches no note
- **THEN** the missing-role-name creation flow starts
