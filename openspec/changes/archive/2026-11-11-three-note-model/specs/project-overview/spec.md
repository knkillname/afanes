# Spec Delta

## ADDED Requirements

### Requirement: Steps belong to their project by containment

A step SHALL belong to the project whose body contains it. Membership MUST NOT depend on a reference, a directory, or a frontmatter key. A project with no task list items has no steps.

#### Scenario: A checkbox is a step of its project

- **WHEN** a project body contains `- [ ] Call the plumber`
- **THEN** the step belongs to that project

#### Scenario: A body link is not a step

- **WHEN** a note links to a project only in its body
- **THEN** the link does not create a step in that project

#### Scenario: A project may have no steps

- **WHEN** a project body has no task list item
- **THEN** the project reports zero steps

### Requirement: A project row reports status, due date, open steps, and next step

Each project row SHALL show its status, optional due date, count of open steps, and next step. An open step SHALL be an unchecked task list item. Checked steps SHALL NOT count as open.

#### Scenario: Row shows the project due date

- **WHEN** a project declares a due date
- **THEN** the row shows that date

#### Scenario: Row without a due date omits it

- **WHEN** a project has no due date
- **THEN** the row shows no due date

#### Scenario: Open count excludes checked steps

- **WHEN** a project has two unchecked steps and one checked step
- **THEN** the row reports two open steps

#### Scenario: A project with no steps reports zero

- **WHEN** a project has no task list item
- **THEN** the row reports zero open steps

#### Scenario: The row shows the next step

- **WHEN** a project has at least one unchecked step
- **THEN** the row names the first one as the next step

### Requirement: The next step is the first unchecked step

A project's next step SHALL be its first unchecked task list item in document order. A project with no unchecked step SHALL have no next step. Dates and owners MUST NOT reorder the steps.

#### Scenario: First unchecked wins

- **WHEN** a project's second step is unchecked and its first is checked
- **THEN** the second step is the next step

#### Scenario: No unchecked step means no next step

- **WHEN** every step of a project is checked
- **THEN** the row reports no next step

#### Scenario: A date does not reorder

- **WHEN** an earlier step has a later plan date than a later step
- **THEN** the earlier step is still the next step

#### Scenario: An owned step can be next

- **WHEN** the first unchecked step declares an owner
- **THEN** it is still the next step and the row marks it as waiting

### Requirement: Project status is not changed by steps

The Projects workspace SHALL NOT change a project's status when its steps change. Checking every step SHALL NOT close the project, and closing a project SHALL NOT change its steps.

#### Scenario: Completed steps leave the project open

- **WHEN** every step of an active project becomes checked
- **THEN** the project remains active and reports zero open steps

#### Scenario: Closing a project leaves steps unchanged

- **WHEN** the user changes a project to `done`
- **THEN** its steps keep their checked state and metadata

### Requirement: The Projects workspace reflects step changes

After a scan, page save, step toggle, step creation, status change, rename, or trash, the Projects workspace SHALL reflect the latest project and step state.

#### Scenario: Checking a step updates the count

- **WHEN** an open step is checked
- **THEN** the project's open count decreases

#### Scenario: Adding a step updates the next step

- **WHEN** a new unchecked step is added before the current next step
- **THEN** the row's next step becomes the new step

#### Scenario: Trashing a project removes it

- **WHEN** a project is moved to trash
- **THEN** it disappears from the Projects workspace

#### Scenario: Viewing projects performs no write

- **WHEN** the Projects workspace is opened or refreshed
- **THEN** no note file is created, changed, or removed

## REMOVED Requirements

### Requirement: Project membership comes from the project reference

**Reason**: There are no action notes, so nothing declares its project through a frontmatter reference. Steps are contained by the project body.

**Migration**: Move each action note's work into its project's body as a task list item.

### Requirement: A project row reports status, due date, open actions, and next action

**Reason**: Actions are gone; the same information is now derived from steps.

**Migration**: None. The row is computed from the project body.

### Requirement: The next action is computed from open actions

**Reason**: There are no action notes and no per-action statuses. The next step is positional.

**Migration**: None. Reorder the steps in the body to change the next step.

### Requirement: Project status is never changed automatically

**Reason**: The behavior is unchanged, but its requirement named actions. It is restated with steps under the new requirement.

**Migration**: None.

### Requirement: The Projects workspace reflects vault changes

**Reason**: The behavior is unchanged, but its requirement named actions. It is restated with steps under the new requirement.

**Migration**: None.
