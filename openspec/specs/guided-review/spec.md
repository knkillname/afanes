# guided-review Specification

## Purpose

Defines the Review entry and guided session that walks pending Inbox items and open projects, reuses explicit processing, and ensures each project has a usable next step.

## Requirements

### Requirement: Review shows the pending count

The workspace SHALL provide a Review entry whose count is the number of pending Inbox notes, due or overdue own steps, waiting steps, and open projects with no open step. The count SHALL update after every capture, step toggle, processing apply, page save, or trash.

#### Scenario: Count combines Inbox and stalled projects

- **WHEN** the vault has three Inbox notes and two projects with no open step
- **THEN** Review shows five pending items

#### Scenario: Processing reduces the count

- **WHEN** an Inbox item is processed
- **THEN** the Review count decreases by one

#### Scenario: Healthy project is not counted

- **WHEN** an open project has at least one unchecked own step
- **THEN** it does not contribute to the Review count

#### Scenario: Due step is counted

- **WHEN** an own step's plan date is today or earlier and it is unchecked
- **THEN** it contributes to the count

#### Scenario: Waiting step is counted

- **WHEN** a step has an owner
- **THEN** it contributes to the count

#### Scenario: Zero pending is shown

- **WHEN** there are no pending items
- **THEN** Review shows zero pending items and starts no session

### Requirement: A review session uses a snapshot queue

Starting Review SHALL snapshot a queue ordered as pending Inbox notes, then due or overdue own steps, then waiting steps, then projects with no open step, then open projects with a next step. Closed projects SHALL be excluded. Notes created during the session SHALL NOT be added.

#### Scenario: Inbox items come first

- **WHEN** a session starts with Inbox notes, due steps, and projects
- **THEN** every Inbox item precedes every step and project

#### Scenario: Due steps precede waiting steps

- **WHEN** the queue contains a due step and a waiting step
- **THEN** the due step comes first

#### Scenario: Waiting steps precede stalled projects

- **WHEN** the queue contains a waiting step and a stalled project
- **THEN** the waiting step comes first

#### Scenario: Stalled projects precede healthy projects

- **WHEN** the session includes a project with no open step and a project with one
- **THEN** the stalled project is reviewed first

#### Scenario: Closed projects are excluded

- **WHEN** a project is done, cancelled, or archived
- **THEN** it is not part of the review queue

#### Scenario: New work waits for the next session

- **WHEN** a step is added during a session
- **THEN** it is not appended to the current queue

### Requirement: Inbox review reuses explicit processing

Each Inbox item in a review session SHALL open the existing processing flow, including the same
capture content, template card choices, and metadata inputs as processing from the Inbox. Applying an
outcome SHALL advance the session; cancelling SHALL leave the capture unchanged and keep the item
pending.

#### Scenario: Apply advances the session

- **WHEN** the user confirms a processing outcome for an Inbox item
- **THEN** the item is applied and the next review item is shown

#### Scenario: Cancel keeps the capture

- **WHEN** the user cancels processing for an Inbox item
- **THEN** the capture remains in `inbox/` and the session stays on that item or skips it

#### Scenario: Outcome is not inferred

- **WHEN** the capture text resembles an action, project, person, or date
- **THEN** the review does not choose an outcome or metadata from that text

#### Scenario: Template cards are available

- **WHEN** an Inbox item in a review session opens the Processing Wizard and the user chooses Reference or Later
- **THEN** the Template field lists every valid reference card and Empty

### Requirement: A project review card shows its next step

Each project in a review session SHALL show the project title, status, optional due date, its next step, and any other open steps. The user SHALL be able to open the project or the next step.

#### Scenario: Project with a next action

- **WHEN** a project has an open step
- **THEN** the card shows that step as the next step

#### Scenario: Other open actions are listed

- **WHEN** a project has more than one open step
- **THEN** the card lists the remaining open steps separately

#### Scenario: Project can be opened from the card

- **WHEN** the user chooses to open the project
- **THEN** the page pane shows the project page

#### Scenario: Next action can be opened from the card

- **WHEN** the user chooses the next step
- **THEN** the page pane shows that project page at the step

### Requirement: A stalled project can gain a next step

When a project has no open step, the review card SHALL offer adding a step, marking the project done, deferring it to `later`, or skipping. Adding a step SHALL require text and SHALL append a task list item to the project body, then refresh the project's next step.

#### Scenario: Add a next step

- **WHEN** the user supplies text for a stalled project's next step
- **THEN** a task list item is appended to the project body and the card shows it as the next step

#### Scenario: Cancel adding changes nothing

- **WHEN** the user cancels the next-step form
- **THEN** the project body is unchanged

#### Scenario: Blank text is rejected

- **WHEN** the user confirms an empty next-step text
- **THEN** no step is added and the form reports that text is required

#### Scenario: Mark the project done

- **WHEN** the user confirms marking a stalled project done
- **THEN** the project status becomes `done` and it leaves the review queue

#### Scenario: Defer the project

- **WHEN** the user confirms deferring a stalled project
- **THEN** the project status becomes `later` and it remains open

#### Scenario: Skip leaves the project stalled

- **WHEN** the user skips a stalled project
- **THEN** the project keeps its status and remains in the next review's pending count

### Requirement: Review advances, skips, and completes

The session SHALL provide Next and Skip for every item. Skip SHALL move to the next item without changing the skipped item. After the last item, the session SHALL show a completion summary and return to the browser.

#### Scenario: Next advances

- **WHEN** the user chooses Next on a project card
- **THEN** the next queued item is shown

#### Scenario: Skip advances without writing

- **WHEN** the user skips an item
- **THEN** the item is unchanged and the next queued item is shown

#### Scenario: Completion summary is shown

- **WHEN** the last item is passed
- **THEN** the session reports how many items were reviewed and skipped and returns to the browser

#### Scenario: Session is not persisted

- **WHEN** the application restarts during a review
- **THEN** no review position is restored and the pending count is recomputed from the vault

### Requirement: Review never changes work by inference

The review SHALL NOT classify captures, change project status, check a step, or create a note without an explicit user choice and confirmation.

#### Scenario: Browsing a review card writes nothing

- **WHEN** a project card is shown without a choice
- **THEN** no project or step changes

#### Scenario: Closing a project is explicit

- **WHEN** a project has no open steps
- **THEN** the review asks the user to choose an outcome and does not close the project automatically

#### Scenario: Checking a step is explicit

- **WHEN** a due step is shown
- **THEN** it is not checked until the user chooses do it now

### Requirement: A due step can be done, postponed, or delegated

Each due or overdue own step SHALL offer do it now, postpone, delegate, open project, and skip. Do it now SHALL check the step and record the actual date. Postpone SHALL replace or add the plan date. Delegate SHALL add an owner and move the step to waiting.

#### Scenario: Do it now checks the step

- **WHEN** the user chooses do it now for a due step
- **THEN** the step is checked and its metadata records the current date as `actual`

#### Scenario: Postpone changes the plan

- **WHEN** the user postpones a due step to a later date
- **THEN** the step's `plan` becomes the new date and `actual` is absent

#### Scenario: Delegate moves the step to waiting

- **WHEN** the user delegates a due step to a person
- **THEN** the step's `owners` gains that name and the step leaves the user's own list

#### Scenario: Open project keeps the session

- **WHEN** the user chooses open project for a step
- **THEN** the project page opens and the session position is unchanged

#### Scenario: Skip changes nothing

- **WHEN** the user skips a due step
- **THEN** the step is unchanged

### Requirement: Waiting steps are reviewed

Each waiting step SHALL show its owners and offer reassign, open project, and skip. Reassign SHALL replace the owners. The review MUST NOT change a waiting step without an explicit choice.

#### Scenario: Waiting card shows its owners

- **WHEN** a waiting step declares `owners: [Ada]`
- **THEN** the card names Ada

#### Scenario: Reassign replaces the owners

- **WHEN** the user reassigns a waiting step to Grace
- **THEN** the metadata's owners become `[Grace]`

#### Scenario: Skip leaves the wait unchanged

- **WHEN** the user skips a waiting step
- **THEN** the owners and dates are unchanged

#### Scenario: Open project from a waiting step

- **WHEN** the user opens the project of a waiting step
- **THEN** the project page is shown

### Requirement: The launch digest reports due work

At launch the application SHALL show a digest of due and overdue own steps. Activating the digest SHALL start the guided review. The digest MUST NOT write to the vault.

#### Scenario: Digest reports the count

- **WHEN** three own steps are due or overdue
- **THEN** the digest reports three

#### Scenario: Activating the digest starts review

- **WHEN** the user activates the digest
- **THEN** the guided session starts

#### Scenario: No due work hides the digest

- **WHEN** no own step is due or overdue
- **THEN** no digest is shown

#### Scenario: The digest writes nothing

- **WHEN** the digest is shown at launch
- **THEN** no note file is created, changed, or removed

### Requirement: Review step text is rendered Markdown

Every step text shown in a review card SHALL be rendered as inline Markdown. This includes the due or
waiting step card, the project card's next step, and the project card's other open steps. Raw Markdown
source MUST NOT appear in the card. Metadata comments remain hidden.

#### Scenario: A link in a due step card is rendered

- **WHEN** a due step's text contains `[Incident notes](<note:Incident notes>)`
- **THEN** the card shows `Incident notes` and not the raw destination syntax

#### Scenario: Emphasis in a due step card is rendered

- **WHEN** a due step's text contains `**Bold** step`
- **THEN** the card shows `Bold step` with emphasis and not the asterisks

#### Scenario: A waiting step card is rendered

- **WHEN** a waiting step's text contains Markdown
- **THEN** the card renders it with the same rule

#### Scenario: A project card's next step is rendered

- **WHEN** a project card's next step contains a link or emphasis
- **THEN** the next-step line renders it and does not show raw syntax

#### Scenario: Other open steps are rendered

- **WHEN** a project card lists other open steps with Markdown
- **THEN** each line renders its Markdown

#### Scenario: Showing a card writes nothing

- **WHEN** a review card is shown
- **THEN** no project or step file changes

#### Scenario: Summary links do not navigate

- **WHEN** a step link in a review card is tapped
- **THEN** the card remains on the current review item and opening the project remains an explicit action
