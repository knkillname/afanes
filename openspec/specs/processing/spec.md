# processing Specification

## Purpose

Defines how an inbox capture becomes Trash, Later, Reference, Project, a log entry, an appended step, or Done now, including the decisions, metadata, confirmation, and safe apply behavior.

## Requirements

### Requirement: Processing is explicit and confirmed

Processing SHALL operate only on a note under `inbox/` and SHALL require an explicit user action and confirmation before any write. It MUST NOT run during startup or scan.

#### Scenario: Preview precedes writes

- **WHEN** the user starts processing a capture
- **THEN** the application shows the outcome and destination and writes nothing until the user confirms

#### Scenario: Preview is insensitive without an outcome

- **WHEN** no processing outcome is selected
- **THEN** the Preview action is insensitive

#### Scenario: Preview waits for required input

- **WHEN** the selected outcome requires a project or a date that is missing or invalid
- **THEN** the Preview action is insensitive

#### Scenario: Cancel changes nothing

- **WHEN** the user cancels the processing preview
- **THEN** the note remains unchanged in `inbox/`

#### Scenario: Non-inbox note is rejected

- **WHEN** processing targets a note outside `inbox/`
- **THEN** the application reports an error and changes no file
### Requirement: The outcome set is fixed

A processed capture SHALL become exactly one of Trash, Later, Reference, Project, Log entry, Append
step, or Done now. The user SHALL choose the outcome; processing MUST NOT infer it.

#### Scenario: One outcome per apply

- **WHEN** a processing plan is applied
- **THEN** exactly one outcome is recorded and the capture leaves the Inbox

#### Scenario: Classification is not inferred

- **WHEN** the capture text contains words that resemble a person, project, date, or action
- **THEN** processing does not choose an outcome or metadata from that text

#### Scenario: A single action is a project

- **WHEN** the user treats one step as the whole commitment
- **THEN** the outcome is a one-step project

#### Scenario: Every fixed outcome is offered

- **WHEN** the Processing Wizard opens for a capture
- **THEN** the outcome list offers Trash, Later, Reference, Project, Log entry, Append step, and Done now

#### Scenario: A log entry is an explicit outcome

- **WHEN** the user chooses Log entry
- **THEN** the capture becomes a log entry and no other outcome is applied

### Requirement: Actionable captures become projects or steps

An actionable capture SHALL become a new project, a step appended to an existing project, or a completed one-step project. The user SHALL choose which; processing MUST NOT infer it.

#### Scenario: A single step becomes a one-step project

- **WHEN** the user marks an actionable capture as a new project with one step
- **THEN** the note becomes `type: project` and is filed under `projects/`

#### Scenario: A multi-step outcome becomes a project

- **WHEN** the user marks an actionable capture as a new multi-step project
- **THEN** the note becomes `type: project` and is filed under `projects/`

#### Scenario: The step joins an existing project

- **WHEN** the user chooses Append step and selects a project
- **THEN** the step is written into that project's body and the capture is trashed

#### Scenario: A quick action is completed immediately

- **WHEN** the user chooses Done now
- **THEN** a one-step project is written with its step ticked and `status: done`

#### Scenario: Actionable capture requires a choice

- **WHEN** the user marks a capture actionable without choosing new project, append, or done
- **THEN** processing does not apply

### Requirement: Appending a step preserves capture detail

When a capture is appended to a project, its first non-blank line SHALL become the step text and the remaining body SHALL be indented beneath that step. The step line and its detail SHALL be written to the target project in one atomic write. The capture SHALL then be moved to trash.

#### Scenario: First line becomes the step

- **WHEN** a capture `Call the plumber` with detail is appended
- **THEN** the project gains `- [ ] Call the plumber` followed by the indented detail

#### Scenario: The capture is trashed after the write

- **WHEN** the append succeeds
- **THEN** the capture is moved to `trash/`

#### Scenario: Failed append leaves both notes unchanged

- **WHEN** the target project changed after the plan was created
- **THEN** the capture stays in `inbox/` and the project is unchanged

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

### Requirement: Project metadata and steps

A project outcome SHALL become `type: project` with a status and an optional due date. Its steps are checkbox items in its body. Processing SHALL preserve any task list item carried by the capture and MUST NOT create steps in another note unless the user chooses Append step.

#### Scenario: Project is filed flat

- **WHEN** a capture becomes a project
- **THEN** the project note is filed directly under `projects/`

#### Scenario: Steps come from the capture body

- **WHEN** the capture body contains task list items
- **THEN** those lines become the project's steps

#### Scenario: Steps are added later

- **WHEN** the user adds a step to a project
- **THEN** a task list item is appended to the project body

#### Scenario: A project may start empty

- **WHEN** the capture body contains no task list item
- **THEN** the project is created with no steps and parses

#### Scenario: Project has no project key

- **WHEN** a project note is written
- **THEN** it does not declare a `project` key

### Requirement: Project outcomes accept role names

The Project and Done now outcomes SHALL accept an optional owner and an optional requester. A
non-blank value SHALL be trimmed and written as `owner` or `asked_by` in the same atomic write as the
classification. A blank value SHALL not write the key. The values MAY match no note and SHALL be
written as plain text. No other outcome SHALL accept these fields.

#### Scenario: Project writes an owner and requester

- **WHEN** the user creates a project with `Sam Rivera` as owner and `Priya Nair` as requester
- **THEN** the project contains `owner: Sam Rivera` and `asked_by: Priya Nair`

#### Scenario: Done now accepts role names

- **WHEN** the user chooses Done now with an owner and requester
- **THEN** the completed project contains both values

#### Scenario: Blank values write no role keys

- **WHEN** the user leaves a role field blank
- **THEN** the corresponding key is absent from the written project

#### Scenario: An unresolved name is accepted

- **WHEN** the user types a role name that matches no note
- **THEN** the value is written unchanged and may be created later from the project page

#### Scenario: Role fields suggest names

- **WHEN** the user types part of an existing note name in a role field
- **THEN** matching note names are offered as suggestions

#### Scenario: Non-project outcomes reject role names

- **WHEN** the selected outcome is Reference, Later, Log entry, Trash, or Append step
- **THEN** no owner or requester field is offered and no role key is written

#### Scenario: Append step does not inherit the project owner

- **WHEN** a capture is appended to a project that has an owner
- **THEN** the appended step has no owner unless the user sets one later

### Requirement: The append target suggests projects

When the user chooses Append step, the project input SHALL suggest existing projects by display title or identity. Selecting a suggestion SHALL target that project's identity. Text that matches no project SHALL be rejected, because a step requires an existing project.

#### Scenario: Typing a title suggests the project

- **WHEN** a project has identity `Home` and display title `Home improvements`
- **THEN** typing part of the title suggests that project

#### Scenario: Typing the identity suggests the project

- **WHEN** the user types `Home` and a project has identity `Home`
- **THEN** that project is suggested

#### Scenario: Selecting a suggestion stores the identity

- **WHEN** the user selects a project whose title differs from its identity
- **THEN** the plan targets the identity, not the title

#### Scenario: Free text that matches no project is rejected

- **WHEN** the user types a project name that matches no project
- **THEN** the plan is rejected and nothing is written

#### Scenario: Duplicate titles are distinct suggestions

- **WHEN** two projects have the same display title
- **THEN** both appear as separate suggestions distinguished by their identities

#### Scenario: Matching ignores case and repeated whitespace

- **WHEN** the user types `home` or `Home,   improvements`
- **THEN** the matching project is suggested

### Requirement: Processing writes a valid status

Processing SHALL write a status valid for the target type. A new project defaults to `active`, a done-now project is `done`, and a reference uses no status or `later`. Processing MUST NOT write `inbox`, or `waiting` on a reference.

#### Scenario: Project defaults to active

- **WHEN** the user creates a project without choosing a status
- **THEN** the project is written with `status: active`

#### Scenario: Done now is done

- **WHEN** the user chooses Done now
- **THEN** the one-step project is written with `status: done`

#### Scenario: Later reference is later

- **WHEN** the user chooses Later
- **THEN** the reference is written with `status: later`

#### Scenario: Inbox is not a status

- **WHEN** a note declares `status: inbox`
- **THEN** parsing reports a validation error

#### Scenario: Waiting reference is invalid

- **WHEN** a reference declares `status: waiting`
- **THEN** parsing reports a validation error

### Requirement: Apply writes then moves atomically

Applying a plan SHALL write every affected note atomically and then move the capture out of `inbox/`. Append step SHALL write the target project first and then trash the capture. A plan MUST be rejected before any change when it is invalid, a source changed after planning, or a destination collides.

#### Scenario: Success leaves the inbox

- **WHEN** processing is confirmed
- **THEN** the capture is written with the chosen classification and moved out of `inbox/`

#### Scenario: Append writes then trashes

- **WHEN** an Append step plan is confirmed
- **THEN** the step is written to the project and the capture is moved to `trash/`

#### Scenario: Changed source aborts

- **WHEN** the capture changed after the plan was created
- **THEN** processing aborts and reports that the note changed

#### Scenario: Changed target aborts the append

- **WHEN** the target project changed after the plan was created
- **THEN** the append aborts and the project is unchanged

#### Scenario: Write failure leaves the source

- **WHEN** the atomic write fails
- **THEN** the capture remains in `inbox/` and no destination note is created

#### Scenario: Failed move is retryable

- **WHEN** the write succeeds but the move fails
- **THEN** the capture remains in `inbox/` with the new metadata and the same plan can be retried

### Requirement: Destination collisions are reported

Processing SHALL abort when the destination filename exists or the target name already identifies
another note in the same scheme. It MUST NOT overwrite the destination or add a numeric suffix.
Append step SHALL abort when the target project no longer exists or changed after planning. The Log
entry outcome SHALL abort when the target date already has a log entry.

#### Scenario: Existing destination file

- **WHEN** `projects/Foo.md` already exists and a capture named `Foo` would be filed there
- **THEN** processing aborts and the capture remains in `inbox/`

#### Scenario: Existing name in the scheme

- **WHEN** another note already uses the target name in the target scheme
- **THEN** processing aborts and reports the collision

#### Scenario: No silent suffix

- **WHEN** a destination collision occurs
- **THEN** the application does not create `Foo 2.md` or overwrite `Foo.md`

#### Scenario: Missing append target

- **WHEN** the target project no longer exists at apply time
- **THEN** the append aborts and the capture remains in `inbox/`

#### Scenario: An occupied log date aborts

- **WHEN** the target date already has a log entry
- **THEN** processing aborts and the capture remains in `inbox/`

### Requirement: Scheme changes are reported

When an outcome changes the capture's reference scheme between `note` and `project`, processing
SHALL report the inbound references that will become unresolved and require confirmation. It MUST
NOT retarget them automatically. The Log entry outcome SHALL instead rewrite inbound `note:`
references to `log:<date>` as defined by `note-identity`.

#### Scenario: Note becomes a project

- **WHEN** a `note:` reference points to a capture that becomes a project
- **THEN** processing reports that the reference will be unresolved and asks for confirmation

#### Scenario: Note stays in the document family

- **WHEN** a capture becomes a reference or is deferred to later
- **THEN** existing `note:` references remain resolved and no scheme warning is shown

#### Scenario: Cancelled scheme change

- **WHEN** the user cancels after the scheme warning
- **THEN** no file changes

#### Scenario: Note becomes a log entry

- **WHEN** a capture referenced as `note:Call the plumber` becomes a log entry dated `2025-10-12`
- **THEN** the referring destination becomes `log:2025-10-12`

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

Processing SHALL preserve the capture text, newline style, and unknown frontmatter keys. It MAY
append a template card's starter body below the capture text, and SHALL modify only the keys owned by
the outcome. The Log entry outcome SHALL preserve the capture body and SHALL NOT append a template
card. Append step SHALL modify only the capture and the target project body.

#### Scenario: Body is preserved

- **WHEN** a capture is processed
- **THEN** its original Markdown text remains a prefix of the body, apart from the classification

#### Scenario: A starter body is appended

- **WHEN** the chosen template card has a starter body
- **THEN** the body contains the capture text followed by the starter body

#### Scenario: Unknown keys are preserved

- **WHEN** the capture has an unknown frontmatter key
- **THEN** the key and value are written back unchanged

#### Scenario: Append preserves the target project

- **WHEN** a step is appended to a project
- **THEN** the rest of the project's frontmatter and body are unchanged

#### Scenario: Other notes are untouched

- **WHEN** a capture is processed without Append step
- **THEN** every other note's content is unchanged

#### Scenario: A log entry keeps the capture body

- **WHEN** a capture is processed into a log entry
- **THEN** its body is preserved and no starter body is appended

### Requirement: Reference and Later use a template card

The Reference and Later outcomes SHALL ask the user to choose a template card or Empty. A card SHALL supply the category and starter body; Empty SHALL supply `general` and no starter body. Processing MUST NOT infer the card from the capture text.

#### Scenario: A card supplies the category

- **WHEN** the user chooses a card with `category: person`
- **THEN** the preview names the category and the note is filed under `reference/person/`

#### Scenario: Empty uses general

- **WHEN** the user chooses Empty
- **THEN** the preview names `general` and the note is filed under `reference/general/`

#### Scenario: The card is not inferred

- **WHEN** the capture text names a person or a place
- **THEN** processing does not choose a card from that text

#### Scenario: The preview names the starter body

- **WHEN** the chosen card has a starter body
- **THEN** the preview reports that the starter body will be added

### Requirement: Processing appends the starter body safely

When a card supplies a starter body, processing SHALL append it to the capture text in the same atomic write as the classification. A card that cannot be read SHALL abort the plan before any write.

#### Scenario: The body is appended in the atomic write

- **WHEN** the user confirms a card outcome
- **THEN** the category and the starter body are written together before the move

#### Scenario: Empty writes no starter body

- **WHEN** the user chooses Empty
- **THEN** the body contains only the capture text and the classification

#### Scenario: An unreadable card aborts

- **WHEN** the chosen card cannot be read at plan time
- **THEN** processing reports the failure and leaves the capture in the inbox

### Requirement: Processing finishes without opening the page editor

Applying a processing plan SHALL end in the success state. It MUST NOT open the created note in the page editor or navigate away from the processing or review flow.

#### Scenario: Success panel remains

- **WHEN** a plan is applied
- **THEN** the wizard shows the success state and no page editor opens

#### Scenario: Review moves on

- **WHEN** processing is part of a review session
- **THEN** the review can record the item and continue without opening the note

#### Scenario: The user can process the next capture

- **WHEN** the user finishes the success state
- **THEN** they return to the inbox or the next review item

### Requirement: Failure is reported and retryable

When processing fails, the application SHALL report an actionable error and leave the capture in `inbox/`. Re-running the same plan MUST be safe.

#### Scenario: Failure leaves the capture

- **WHEN** any processing step fails
- **THEN** the capture remains available in `inbox/`

#### Scenario: Retry completes

- **WHEN** the user retries a previously failed plan after the cause is fixed
- **THEN** the note is processed once and leaves `inbox/`

### Requirement: A capture can become a log entry

The Log entry outcome SHALL turn an inbox capture into `type: log`, move it to the folder its date
selects, and use the capture's existing `date`. It SHALL preserve the capture body and title, SHALL
write no category, status, due date, or requester, and SHALL NOT ask for a template card. When the
capture has no date, the outcome SHALL use the file's last-modified date for this conversion.

#### Scenario: A dated capture becomes a log entry

- **WHEN** a capture dated `2025-10-12` is processed as Log entry
- **THEN** it becomes `type: log` and is filed at `log/2025/10/2025-10-12.md`

#### Scenario: The title is preserved

- **WHEN** a capture with the heading `A quiet Tuesday` becomes a log entry
- **THEN** the entry's heading remains `A quiet Tuesday`

#### Scenario: No card is requested

- **WHEN** the user selects Log entry
- **THEN** the wizard does not ask for a template card

#### Scenario: An undated capture uses its last-modified date

- **WHEN** an undated capture is processed as Log entry
- **THEN** the entry's date is the file's last-modified calendar date

#### Scenario: The conversion is refused on an occupied date

- **WHEN** the capture's date already has a log entry
- **THEN** processing reports the conflict and the capture stays in the inbox

#### Scenario: The capture leaves the inbox

- **WHEN** the log outcome succeeds
- **THEN** the capture is no longer under `inbox/`

### Requirement: A log outcome writes no workflow labels

The Log entry outcome SHALL write only `type: log` and `date`. It MUST NOT write `category`,
`status`, `due_date`, `asked_by`, or `owner`, and it SHALL remove those keys if the capture carried
them.

#### Scenario: No status is written

- **WHEN** a capture becomes a log entry
- **THEN** the resulting note has no `status` key

#### Scenario: No due date is written

- **WHEN** a capture becomes a log entry
- **THEN** the resulting note has no `due_date` key

#### Scenario: No requester is written

- **WHEN** a capture becomes a log entry
- **THEN** the resulting note has no `asked_by` key

#### Scenario: No owner is written

- **WHEN** a capture becomes a log entry
- **THEN** the resulting note has no `owner` key
