# Spec Delta

## MODIFIED Requirements

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

#### Scenario: A log entry is an explicit outcome

- **WHEN** the user chooses Log entry
- **THEN** the capture becomes a log entry and no other outcome is applied

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

## ADDED Requirements

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
`status`, `due_date`, or `asked_by`, and it SHALL remove those keys if the capture carried them.

#### Scenario: No status is written

- **WHEN** a capture becomes a log entry
- **THEN** the resulting note has no `status` key

#### Scenario: No due date is written

- **WHEN** a capture becomes a log entry
- **THEN** the resulting note has no `due_date` key

#### Scenario: No requester is written

- **WHEN** a capture becomes a log entry
- **THEN** the resulting note has no `asked_by` key
