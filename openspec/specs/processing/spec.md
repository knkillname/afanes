# processing Specification

## Purpose

Defines how an inbox capture becomes a trash, later, reference, action, or project note, including the decisions, metadata, confirmation, and safe apply behavior.

## Requirements

### Requirement: Processing is explicit and confirmed

Processing SHALL operate only on a note under `inbox/` and SHALL require an explicit user action and confirmation before any write. It MUST NOT run during startup or scan.

#### Scenario: Preview precedes writes

- **WHEN** the user starts processing a capture
- **THEN** the application shows the outcome and destination and writes nothing until the user confirms

#### Scenario: Cancel changes nothing

- **WHEN** the user cancels the processing preview
- **THEN** the note remains unchanged in `inbox/`

#### Scenario: Non-inbox note is rejected

- **WHEN** processing targets a note outside `inbox/`
- **THEN** the application reports an error and changes no file

### Requirement: The outcome set is fixed

A processed capture SHALL become exactly one of Trash, Later, Reference, Action, or Project. The user SHALL choose the outcome; processing MUST NOT infer it.

#### Scenario: One outcome per apply

- **WHEN** a processing plan is applied
- **THEN** exactly one outcome is recorded and the note moves to exactly one destination

#### Scenario: Classification is not inferred

- **WHEN** the capture text contains words that resemble a person, project, date, or action
- **THEN** processing does not choose an outcome or metadata from that text

### Requirement: Actionable captures become actions or projects

When the user marks a capture actionable, a single-step item SHALL become an action and a multi-step outcome SHALL become a project. The user SHALL choose which.

#### Scenario: Single step becomes an action

- **WHEN** the user marks an actionable capture as a single step
- **THEN** the note becomes type `action` and is filed under `actions/`

#### Scenario: Multi-step outcome becomes a project

- **WHEN** the user marks an actionable capture as a multi-step outcome
- **THEN** the note becomes type `project` and is filed under `projects/`

#### Scenario: Actionable capture requires a choice

- **WHEN** the user marks a capture actionable without choosing action or project
- **THEN** processing does not apply

### Requirement: Non-actionable captures become trash, later, or reference

When the user marks a capture non-actionable, it SHALL become Trash, Later, or Reference. Trash discards recoverably; Later defers a reference; Reference keeps an available reference.

#### Scenario: Trash discards recoverably

- **WHEN** the user chooses Trash
- **THEN** the note moves to `trash/` and is no longer in the Inbox

#### Scenario: Later defers a reference

- **WHEN** the user chooses Later
- **THEN** the note becomes `type: reference` with `status: later` and is filed under `reference/`

#### Scenario: Reference stays available

- **WHEN** the user chooses Reference
- **THEN** the note becomes `type: reference` with no status and is filed under `reference/`

### Requirement: Action metadata and status

An action outcome SHALL allow a status, an optional due date, zero or more people, and an optional project. The default status SHALL be `active`; a delegated action SHALL use `waiting`; a scheduled action SHALL carry a due date.

#### Scenario: Default action is active

- **WHEN** the user creates an action without choosing a status
- **THEN** the note is written with `status: active`

#### Scenario: Delegated action waits

- **WHEN** the user delegates an action to a person
- **THEN** the action is written with `status: waiting` and that `person:` reference

#### Scenario: Scheduled action carries a due date

- **WHEN** the user schedules an action for a calendar date
- **THEN** the action carries that `due_date`

#### Scenario: Unresolved person is allowed

- **WHEN** the user assigns a person with no page yet
- **THEN** the action keeps the `person:` reference and reports it as unresolved

#### Scenario: Completed quick action is done

- **WHEN** the user completes a quick action immediately
- **THEN** the action is written with `status: done`

### Requirement: Project metadata and steps

A project outcome SHALL become `type: project` with a status and optional due date and people. Project steps SHALL be action notes linked by the `project` key; processing SHALL NOT create steps in the same apply.

#### Scenario: Project is filed flat

- **WHEN** a capture becomes a project
- **THEN** the project note is filed directly under `projects/`

#### Scenario: Steps are added later

- **WHEN** the user adds a step to a project
- **THEN** it is an action note under `actions/` with a `project:` reference

#### Scenario: Project has no project key

- **WHEN** a project note is written
- **THEN** it does not declare a `project` key

### Requirement: Reference outcome is uncategorized

The Reference and Later outcomes SHALL create uncategorized references. Processing SHALL NOT assign a person, place, or other category.

#### Scenario: Reference has no category

- **WHEN** the user chooses Reference
- **THEN** the note has `type: reference` and no `category` key

#### Scenario: Later has no category

- **WHEN** the user chooses Later
- **THEN** the note has `type: reference`, `status: later`, and no `category` key

### Requirement: Status vocabulary is explicit

Captures SHALL have no status. Actions and projects SHALL allow `active`, `waiting`, `done`, `cancelled`, `archived`, and `later`. References SHALL allow `later` and `archived`, or no status. `inbox` SHALL NOT be a valid status.

#### Scenario: Capture has no status

- **WHEN** a note is captured
- **THEN** it has no `status` key

#### Scenario: Action status is valid

- **WHEN** an action declares `status: waiting`
- **THEN** the note parses successfully

#### Scenario: Later reference is valid

- **WHEN** a reference declares `status: later`
- **THEN** the note parses successfully

#### Scenario: Inbox is not a status

- **WHEN** a note declares `status: inbox`
- **THEN** parsing reports a validation error

#### Scenario: Waiting reference is invalid

- **WHEN** a reference declares `status: waiting`
- **THEN** parsing reports a validation error

### Requirement: Apply writes then moves atomically

Applying a processing plan SHALL write the classified frontmatter atomically to the source note, then move it to the destination. It MUST abort before any change when the plan is invalid, the source changed after planning, or the destination collides. On success the note leaves `inbox/`.

#### Scenario: Success leaves the inbox

- **WHEN** processing is confirmed
- **THEN** the note is written with the chosen metadata and moved out of `inbox/`

#### Scenario: Changed source aborts

- **WHEN** the source note changed after the plan was created
- **THEN** processing aborts and reports that the note changed

#### Scenario: Write failure leaves the source

- **WHEN** the atomic write fails
- **THEN** the note remains in `inbox/` and no destination note is created

#### Scenario: Failed move is retryable

- **WHEN** the write succeeds but the move fails
- **THEN** the note remains in `inbox/` with the new metadata and the same plan can be retried

### Requirement: Destination collisions are reported

Processing SHALL abort when the destination filename exists or the target name already identifies another note in the same scheme. It MUST NOT overwrite the destination or add a numeric suffix.

#### Scenario: Existing destination file

- **WHEN** `actions/Foo.md` already exists and a capture named `Foo` would be filed there
- **THEN** processing aborts and the capture remains in `inbox/`

#### Scenario: Existing name in the scheme

- **WHEN** another note already uses the target name in the target scheme
- **THEN** processing aborts and reports the collision

#### Scenario: No silent suffix

- **WHEN** a destination collision occurs
- **THEN** the application does not create `Foo 2.md` or overwrite `Foo.md`

### Requirement: Scheme changes are reported

When an outcome changes the note's reference scheme, processing SHALL report the inbound references that will become unresolved and require confirmation. It MUST NOT retarget them automatically.

#### Scenario: Note becomes a project

- **WHEN** a `note:` reference points to a capture that becomes a project
- **THEN** processing reports that the reference will be unresolved and asks for confirmation

#### Scenario: Note stays in the document family

- **WHEN** a capture becomes an action or an uncategorized reference
- **THEN** existing `note:` references remain resolved and no scheme warning is shown

#### Scenario: Cancelled scheme change

- **WHEN** the user cancels after the scheme warning
- **THEN** no file changes

### Requirement: Trash reports inbound references

The Trash outcome SHALL report how many references point to the note before confirmation. It SHALL move the note to `trash/` without rewriting any referring note.

#### Scenario: Inbound count is shown

- **WHEN** a referenced capture is sent to Trash
- **THEN** the preview reports the inbound reference count before confirmation

#### Scenario: Referring notes are untouched

- **WHEN** the user confirms Trash
- **THEN** no referring note is modified and its reference becomes unresolved

#### Scenario: Cancelled Trash

- **WHEN** the user cancels the Trash preview
- **THEN** the note remains in `inbox/`

### Requirement: Processing preserves content

Processing SHALL preserve the body, newline style, and unknown frontmatter keys of the capture. It SHALL modify only the keys owned by the chosen outcome and MUST NOT modify any other note.

#### Scenario: Body is preserved

- **WHEN** a capture is processed
- **THEN** its Markdown body is unchanged

#### Scenario: Unknown keys are preserved

- **WHEN** the capture has an unknown frontmatter key
- **THEN** the key and value are written back unchanged

#### Scenario: Other notes are untouched

- **WHEN** a capture is processed
- **THEN** every other note's content is unchanged

### Requirement: Failure is reported and retryable

When processing fails, the application SHALL report an actionable error and leave the capture in `inbox/`. Re-running the same plan MUST be safe.

#### Scenario: Failure leaves the capture

- **WHEN** any processing step fails
- **THEN** the capture remains available in `inbox/`

#### Scenario: Retry completes

- **WHEN** the user retries a previously failed plan after the cause is fixed
- **THEN** the note is processed once and leaves `inbox/`
