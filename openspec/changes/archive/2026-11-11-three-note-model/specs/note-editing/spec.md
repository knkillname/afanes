# Spec Delta

## ADDED Requirements

### Requirement: Steps render as structured rows

Read mode SHALL render a project's steps as rows showing the step text, checked state, owners, plan and actual dates, and tags. The metadata comment SHALL be hidden from the rendered text. Ticking or unticking a step SHALL rewrite only that line atomically.

#### Scenario: A step shows its metadata

- **WHEN** a step declares owners, dates, and tags
- **THEN** the row shows them as labels rather than raw syntax

#### Scenario: The comment is hidden

- **WHEN** a project body is rendered
- **THEN** the metadata comment does not appear as body text

#### Scenario: Ticking a step updates the line

- **WHEN** the user ticks a step in read mode
- **THEN** the checkbox and its `actual` date are written and the rest of the file is unchanged

#### Scenario: Unticking removes the actual date

- **WHEN** the user unticks a step
- **THEN** `actual` is removed and `plan` is kept

### Requirement: New page type follows the project or note scheme

Creating a page from an unresolved reference SHALL derive its type and default folder from the reference scheme: `note:` creates an uncategorized reference and `project:` creates a project. The draft SHALL open in edit mode with a level-1 heading containing the reference name and an otherwise empty body.

#### Scenario: Note scheme creates an uncategorized reference

- **WHEN** the user creates a page from `note:Quarterly budget`
- **THEN** the draft has type `reference`, no category, and defaults to `reference/Quarterly budget.md`

#### Scenario: Project scheme creates a project

- **WHEN** the user creates a page from `project:Release 1.0`
- **THEN** the draft has type `project` and defaults to `projects/Release 1.0.md`

#### Scenario: Heading preserves the reference wording

- **WHEN** the user creates a page from `note:Q1: Planning?`
- **THEN** the draft heading reads `# Q1: Planning?` while the identity is `Q1 Planning`

### Requirement: The page edits the body and the four labels

Edit mode SHALL present the complete Markdown body, including its headings and steps, as raw text, along with a label form for type, category, status, and due date. Category SHALL be offered only for references and due date only for projects. Status choices SHALL follow the selected type. An invalid label value SHALL block the save and show an inline error.

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

## MODIFIED Requirements

### Requirement: Internal links navigate from read mode

A tap on an internal reference in read mode SHALL resolve the destination against the current name catalog. A resolved reference SHALL open its target page. An unresolved reference SHALL open a new page draft for that reference. An ambiguous reference SHALL show every candidate and SHALL NOT choose one. External links, attachment destinations, and unsafe schemes SHALL remain inert.

#### Scenario: Resolved link opens its target

- **WHEN** the user taps `[Ada](note:Ada)` in read mode and exactly one note named `Ada` exists
- **THEN** the page pane opens that note

#### Scenario: Unresolved link starts a draft

- **WHEN** the user taps a `note:` reference that matches no page
- **THEN** a new page draft opens in edit mode for that reference name

#### Scenario: Ambiguous link asks

- **WHEN** two pages in the same scheme share the referenced name
- **THEN** the page pane lists both candidates and opens neither until one is chosen

#### Scenario: External link is inert

- **WHEN** the user taps an `https:`, `mailto:`, or attachment destination
- **THEN** no page opens, no note changes, and no external program is launched

#### Scenario: Unsafe scheme is inert

- **WHEN** the user taps a `javascript:` destination
- **THEN** no page opens and no note changes

### Requirement: Type changes preview stranded references

Changing a note's type can move it between the `note` and `project` schemes. Before applying such a change, the application SHALL list the inbound references that will become unresolved and SHALL require confirmation. A category change MUST NOT change resolution; it only moves the file.

#### Scenario: Scheme change is previewed

- **WHEN** a note referenced as `note:Prepare report` is changed to a project
- **THEN** the confirmation lists the notes whose `note:Prepare report` references will become unresolved

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

## REMOVED Requirements

### Requirement: New page type follows the reference scheme

**Reason**: The `person` scheme no longer exists, so the old scenario no longer applies. The remaining behavior is restated under the new requirement.

**Migration**: Create person pages from `note:Name` and set the category in the editor.

### Requirement: The page edits the raw body and the labels

**Reason**: The label set changed; `people` and `project` are gone and category is free form. The behavior is restated under the new requirement.

**Migration**: Edit relations as body links and categories as free-form labels.
