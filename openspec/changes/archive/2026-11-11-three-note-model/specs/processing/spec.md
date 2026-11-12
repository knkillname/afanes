# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: The outcome set is fixed

A processed capture SHALL become exactly one of Trash, Later, Reference, Project, Append step, or Done now. The user SHALL choose the outcome; processing MUST NOT infer it.

#### Scenario: One outcome per apply

- **WHEN** a processing plan is applied
- **THEN** exactly one outcome is recorded and the capture leaves the Inbox

#### Scenario: Classification is not inferred

- **WHEN** the capture text contains words that resemble a person, project, date, or action
- **THEN** processing does not choose an outcome or metadata from that text

#### Scenario: A single action is a project

- **WHEN** the user treats one step as the whole commitment
- **THEN** the outcome is a one-step project, not an action note

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

Processing SHALL abort when the destination filename exists or the target name already identifies another note in the same scheme. It MUST NOT overwrite the destination or add a numeric suffix. Append step SHALL abort when the target project no longer exists or changed after planning.

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

### Requirement: Scheme changes are reported

When an outcome changes the capture's reference scheme, processing SHALL report the inbound references that will become unresolved and require confirmation. It MUST NOT retarget them automatically.

#### Scenario: Note becomes a project

- **WHEN** a `note:` reference points to a capture that becomes a project
- **THEN** processing reports that the reference will be unresolved and asks for confirmation

#### Scenario: Note stays in the document family

- **WHEN** a capture becomes a reference or is deferred to later
- **THEN** existing `note:` references remain resolved and no scheme warning is shown

#### Scenario: Cancelled scheme change

- **WHEN** the user cancels after the scheme warning
- **THEN** no file changes

### Requirement: Processing preserves content

Processing SHALL preserve the body, newline style, and unknown frontmatter keys of the capture. It SHALL modify only the keys owned by the outcome. Append step SHALL modify only the capture and the target project body.

#### Scenario: Body is preserved

- **WHEN** a capture is processed
- **THEN** its Markdown body is unchanged, apart from the classification

#### Scenario: Unknown keys are preserved

- **WHEN** the capture has an unknown frontmatter key
- **THEN** the key and value are written back unchanged

#### Scenario: Append preserves the target project

- **WHEN** a step is appended to a project
- **THEN** the rest of the project's frontmatter and body are unchanged

#### Scenario: Other notes are untouched

- **WHEN** a capture is processed without Append step
- **THEN** every other note's content is unchanged

## REMOVED Requirements

### Requirement: Actionable captures become actions or projects

**Reason**: `action` is no longer a note type. A single step is a one-step project, or it joins an existing project.

**Migration**: Convert each action note into a project whose body contains one step, or append the step to its project and trash the action note.

### Requirement: Action metadata and status

**Reason**: Actions are steps, not notes. Status, due date, and ownership belong to the project; ownership on a step is expressed through `owners`.

**Migration**: Move `status` and `due_date` to the project. Replace `people` with body links or step `owners`.

### Requirement: Name entry suggests pages by title and identity

**Reason**: The people field is gone, and Append step targets an existing project only. The behavior is restated under the new append-target requirement.

**Migration**: None. Select the target project from the existing suggestions.

### Requirement: Status vocabulary is explicit

**Reason**: `action` is not a type, and the type vocabulary now lives in the `note-model` capability. Processing keeps only its outcome defaults under the new requirement.

**Migration**: None. Statuses are unchanged for projects and references.

