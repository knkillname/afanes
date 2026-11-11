# guided-review Specification

## Purpose

Defines the Review entry and guided session that walks pending Inbox items and open projects, reuses explicit processing, and ensures each project has a usable next step.

## Requirements

### Requirement: Review shows the pending count

The workspace SHALL provide a Review entry whose count is the number of pending Inbox notes plus open projects with no open action. The count SHALL update after every capture, processing apply, page save, or trash.

#### Scenario: Count combines Inbox and stalled projects

- **WHEN** the vault has three Inbox notes and two projects with no open action
- **THEN** Review shows five pending items

#### Scenario: Healthy project is not counted

- **WHEN** an open project has at least one open action
- **THEN** it does not contribute to the Review count

#### Scenario: Processing reduces the count

- **WHEN** an Inbox item is processed
- **THEN** the Review count decreases by one

#### Scenario: Zero pending is shown

- **WHEN** there are no Inbox notes and no stalled projects
- **THEN** Review shows zero pending items and starts no session

### Requirement: A review session uses a snapshot queue

Starting Review SHALL snapshot a queue ordered as pending Inbox notes, then projects with no next action, then open projects with a next action for confirmation. Closed projects SHALL be excluded. Notes created during the session SHALL NOT be added to the current queue.

#### Scenario: Inbox items come first

- **WHEN** a review session starts with Inbox notes and projects
- **THEN** every Inbox item precedes every project

#### Scenario: Stalled projects precede healthy projects

- **WHEN** the session includes a project with no next action and a project with one
- **THEN** the stalled project is reviewed first

#### Scenario: Closed projects are excluded

- **WHEN** a project is done, cancelled, or archived
- **THEN** it is not part of the review queue

#### Scenario: New work waits for the next session

- **WHEN** an Inbox item is processed into a new project during a session
- **THEN** that project is not appended to the current queue

### Requirement: Inbox review reuses explicit processing

Each Inbox item in a review session SHALL open the existing processing flow. Applying an outcome SHALL advance the session; cancelling SHALL leave the capture unchanged and keep the item pending.

#### Scenario: Apply advances the session

- **WHEN** the user confirms a processing outcome for an Inbox item
- **THEN** the item is applied and the next review item is shown

#### Scenario: Cancel keeps the capture

- **WHEN** the user cancels processing for an Inbox item
- **THEN** the capture remains in `inbox/` and the session stays on that item or skips it

#### Scenario: Outcome is not inferred

- **WHEN** the capture text resembles an action, project, person, or date
- **THEN** the review does not choose an outcome or metadata from that text

### Requirement: A project review card shows its next step

Each project in a review session SHALL show the project title, status, optional due date, its next action, and any other open actions. The user SHALL be able to open the project or the next action.

#### Scenario: Project with a next action

- **WHEN** a project has an open action
- **THEN** the card shows that action as the next step

#### Scenario: Other open actions are listed

- **WHEN** a project has more than one open action
- **THEN** the card lists the remaining open actions separately

#### Scenario: Project can be opened from the card

- **WHEN** the user chooses to open the project
- **THEN** the page pane shows the project page

#### Scenario: Next action can be opened from the card

- **WHEN** the user chooses the next action
- **THEN** the page pane shows that action page

### Requirement: A stalled project can gain a next action

When a project has no open action, the review card SHALL offer creating a next action, marking the project done, deferring it to `later`, or skipping. Creating an action SHALL require a title and SHALL write an action with the project reference, then refresh the project's next step.

#### Scenario: Create a next action

- **WHEN** the user supplies a title for a stalled project's next action
- **THEN** an action is created under `actions/` with `project:` pointing at the project and the project card shows it as the next step

#### Scenario: Cancel creation changes nothing

- **WHEN** the user cancels the next-action form
- **THEN** no action file is created and the project is unchanged

#### Scenario: Blank title is rejected

- **WHEN** the user confirms an empty next-action title
- **THEN** no action is created and the form reports that a title is required

#### Scenario: Mark the project done

- **WHEN** the user confirms marking a stalled project done
- **THEN** the project status becomes `done` and it leaves the review queue

#### Scenario: Defer the project

- **WHEN** the user confirms deferring a stalled project
- **THEN** the project status becomes `later` and it remains open

#### Scenario: Skip leaves the project stalled

- **WHEN** the user skips a stalled project
- **THEN** the project keeps its status and remains in the next review session's pending count

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

The review SHALL NOT classify captures, change project status, complete actions, or create notes without an explicit user choice and confirmation.

#### Scenario: Browsing a review card writes nothing

- **WHEN** a project card is shown without an action
- **THEN** no project or action file changes

#### Scenario: Closing a project is explicit

- **WHEN** a project has no open actions
- **THEN** the review asks the user to choose an outcome and does not close the project automatically
