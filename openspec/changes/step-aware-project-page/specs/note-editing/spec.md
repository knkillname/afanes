# Spec Delta

## MODIFIED Requirements

### Requirement: Steps render as structured rows

Read mode SHALL render a project body as ordered prose blocks and task-list blocks. A task-list block SHALL render as an accent-tinted card of step rows showing checked state, text, owners, plan and actual dates, and tags. The metadata comment SHALL be hidden from rendered text. Ticking or unticking a step SHALL rewrite only that line atomically.

#### Scenario: A step shows its metadata

- **WHEN** a step declares owners, dates, and tags
- **THEN** the row shows them as labels rather than raw syntax

#### Scenario: Prose and steps keep document order

- **WHEN** a project body contains prose before and after a task list
- **THEN** the page shows the prose, the step card, and the following prose in body order

#### Scenario: A contiguous task list is one card

- **WHEN** a project body contains several task list items separated only by blank lines
- **THEN** the page groups them into one step card

#### Scenario: Unsupported body shape falls back to Markdown

- **WHEN** a task list cannot be separated into step rows without changing the surrounding Markdown
- **THEN** that block renders as ordinary Markdown and no content is dropped or rewritten

#### Scenario: The comment is hidden

- **WHEN** a project body is rendered
- **THEN** the metadata comment does not appear as body text

#### Scenario: Ticking a step updates the line

- **WHEN** the user ticks a step in read mode
- **THEN** the checkbox and its `actual` date are written and the rest of the file is unchanged

#### Scenario: Unticking removes the actual date

- **WHEN** the user unticks a step
- **THEN** `actual` is removed and `plan` is kept

## ADDED Requirements

### Requirement: Step row text is rendered Markdown

Step row text SHALL render inline Markdown, including internal references. A tap on an internal reference in a step row SHALL follow the existing read-mode navigation rules. External, attachment, and unsafe destinations SHALL remain inert.

#### Scenario: A link in a step row opens its target

- **WHEN** a step row contains `[Sam Rivera](<note:Sam Rivera>)` and exactly one note named `Sam Rivera` exists
- **THEN** tapping the label opens that note

#### Scenario: An ambiguous step link asks

- **WHEN** two notes share the referenced name
- **THEN** the page lists both candidates and opens neither until one is chosen

#### Scenario: An external step link is inert

- **WHEN** a step row contains an `https:` or attachment link
- **THEN** no page opens and no external program is launched

### Requirement: Step rows expose plan and owner actions

Every step row SHALL expose a calendar action and a person action. The calendar action SHALL set or clear the step's plan date. The person action SHALL manage the complete owner list. Both actions SHALL be present but muted at rest, SHALL become emphasized on hover or keyboard focus, and SHALL remain reachable on touch devices.

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

### Requirement: Project page shows status and due date

Read mode SHALL show a project meta row under the page title with its status and optional due date. The due date SHALL expose a calendar action that sets or clears it. The action SHALL be present but muted at rest and emphasized on hover or keyboard focus. The due-date field SHALL remain available in edit mode.

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
