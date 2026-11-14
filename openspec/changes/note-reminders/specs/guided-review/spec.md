# Spec Delta

## MODIFIED Requirements

### Requirement: Review shows the pending count

The workspace SHALL provide a Review entry whose count is the number of due reminders, pending Inbox
notes, due or overdue own steps, waiting steps, and open projects with no open step. The count SHALL
update after every capture, step toggle, processing apply, page save, trash, reminder dismissal, and
due-occurrence refresh.

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

#### Scenario: A due reminder is counted

- **WHEN** a reminder is due and no other work is pending
- **THEN** it contributes one item to the count

#### Scenario: Dismissing a reminder reduces the count

- **WHEN** a due reminder is dismissed
- **THEN** the Review count decreases by one

#### Scenario: A newly due reminder updates the count

- **WHEN** a reminder becomes due while the application is open
- **THEN** the Review count updates within 15 seconds

### Requirement: A review session uses a snapshot queue

Starting Review SHALL snapshot a queue ordered as due reminders, then pending Inbox notes, then due
or overdue own steps, then waiting steps, then projects with no open step, then open projects with a
next step. Due reminders SHALL be ordered most overdue first. Closed projects SHALL be excluded.
Work created or becoming due during the session SHALL NOT be added.

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

#### Scenario: Due reminders precede Inbox captures

- **WHEN** a session contains a due reminder and an Inbox capture
- **THEN** the reminder card comes first

#### Scenario: Due reminders are ordered by age

- **WHEN** two reminders are due at different times
- **THEN** the reminder whose latest occurrence is older comes first

#### Scenario: A reminder becoming due waits for the next session

- **WHEN** a reminder becomes due during an active session
- **THEN** it is not appended to the current queue

### Requirement: The launch digest reports due work

At launch the application SHALL show a digest of due reminders and due or overdue own steps.
Activating the digest SHALL start the guided review. The digest MUST NOT write to the vault.

#### Scenario: Digest reports the count

- **WHEN** three own steps are due or overdue
- **THEN** the digest reports three

#### Scenario: Activating the digest starts review

- **WHEN** the user activates the digest
- **THEN** the guided session starts

#### Scenario: No due work hides the digest

- **WHEN** no own step is due or overdue and no reminder is due
- **THEN** no digest is shown

#### Scenario: The digest writes nothing

- **WHEN** the digest is shown at launch
- **THEN** no note file is created, changed, or removed

#### Scenario: A reminder alone shows the digest

- **WHEN** a reminder is due at launch and no step is due
- **THEN** the digest reports one item and offers Start Review

#### Scenario: The digest uses neutral item wording

- **WHEN** the digest counts steps and reminders together
- **THEN** it reports “items” rather than “due steps”

## ADDED Requirements

### Requirement: A due reminder is reviewed

Each due reminder in a review session SHALL show the note title and a relative time, with Open Page,
Dismiss, and Skip actions. Open Page SHALL open the note without dismissing it. Dismiss SHALL record
the occurrence and advance. Skip SHALL change nothing. The card MUST NOT change the note body or
status.

#### Scenario: A reminder card shows the note and relative time

- **WHEN** a reminder is due
- **THEN** the card shows the note title and a relative time such as “2 hours ago”

#### Scenario: Open Page opens the note

- **WHEN** the user chooses Open Page
- **THEN** the reminder's note opens and the reminder stays due

#### Scenario: Dismiss records the occurrence

- **WHEN** the user chooses Dismiss
- **THEN** the occurrence is recorded and the session advances

#### Scenario: Dismiss preserves the note

- **WHEN** the user dismisses a reminder
- **THEN** the note body and status are unchanged

#### Scenario: Skip leaves the reminder due

- **WHEN** the user chooses Skip
- **THEN** no file is written and the reminder remains due for the next session

#### Scenario: A failed dismissal leaves the reminder due

- **WHEN** the dismissal cannot be written
- **THEN** the failure is reported and the reminder remains due
