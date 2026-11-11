# Spec Delta

## Purpose

Defines the Projects workspace: which projects are open or closed, how actions are attributed through the `project` frontmatter reference, and how due dates, action counts, and the computed next action are presented.

## ADDED Requirements

### Requirement: Projects are grouped by status

The Projects workspace SHALL list every parsed project note under Active, Waiting, Later, or Closed. A project with no status SHALL appear under Active. Closed SHALL contain `done`, `cancelled`, and `archived` projects and SHALL be collapsed by default.

#### Scenario: Active project is current

- **WHEN** a project has `status: active`
- **THEN** it appears under Active

#### Scenario: Waiting project is current

- **WHEN** a project has `status: waiting`
- **THEN** it appears under Waiting

#### Scenario: Deferred project is separate

- **WHEN** a project has `status: later`
- **THEN** it appears under Later

#### Scenario: Project without a status is active

- **WHEN** a project has no `status` key
- **THEN** it appears under Active and the file is not modified

#### Scenario: Completed project is closed

- **WHEN** a project has `status: done`, `cancelled`, or `archived`
- **THEN** it appears under Closed

#### Scenario: Closed group starts collapsed

- **WHEN** the Projects workspace opens
- **THEN** the Closed group is collapsed and closed projects are not listed until expanded

### Requirement: Project membership comes from the project reference

An action SHALL belong to a project only when its `project` frontmatter reference resolves uniquely to that project. Body links to the project SHALL NOT count as steps. An action with no project, an unresolved project, or an ambiguous project reference SHALL NOT be attributed to any project.

#### Scenario: Action with a project reference counts

- **WHEN** an action declares `project: "project:Turing Machine"` and exactly one project named `Turing Machine` exists
- **THEN** the action counts as a step of that project

#### Scenario: Body link does not count

- **WHEN** a note links to a project only in its body
- **THEN** it does not appear in the project's action counts

#### Scenario: Ambiguous project reference is not attributed

- **WHEN** two projects share the referenced identity
- **THEN** the action is not attributed to either project

#### Scenario: Unresolved project reference is not attributed

- **WHEN** an action references a project that has no page
- **THEN** the action is not attributed to any project

#### Scenario: Action without a project is unassigned

- **WHEN** an action has no `project` key
- **THEN** it is not attributed to any project

### Requirement: A project row reports status, due date, open actions, and next action

Each project row SHALL show its status, optional due date, count of open actions, and next action. An open action SHALL be an action with no status or with `active` or `waiting`; `done`, `cancelled`, `archived`, and `later` actions SHALL NOT count as open.

#### Scenario: Row shows the project due date

- **WHEN** a project declares a due date
- **THEN** the row shows that date

#### Scenario: Row without a due date omits it

- **WHEN** a project has no due date
- **THEN** the row shows no due date

#### Scenario: Open count excludes completed actions

- **WHEN** a project has two active actions and one done action
- **THEN** the row reports two open actions

#### Scenario: Waiting action counts as open

- **WHEN** a project has one waiting action
- **THEN** the row reports one open action

#### Scenario: Later action is not open

- **WHEN** a project has one later action and no active or waiting actions
- **THEN** the row reports zero open actions

### Requirement: The next action is computed from open actions

A project's next action SHALL be the open action with the earliest due date. When no open action has a due date, `active` SHALL rank before `waiting`, then the display title SHALL break ties. A project with no open action SHALL have no next action.

#### Scenario: Earliest due date wins

- **WHEN** a project has open actions due on different dates
- **THEN** the next action is the earliest due action

#### Scenario: Active ranks before waiting without dates

- **WHEN** a project's open actions have no due dates
- **THEN** an active action is chosen before a waiting action

#### Scenario: Title breaks a tie

- **WHEN** open actions share a due date and status
- **THEN** the alphabetically first display title is chosen

#### Scenario: No open action means no next action

- **WHEN** a project has no open actions
- **THEN** the row reports no next action

### Requirement: Project status is never changed automatically

The Projects workspace SHALL NOT change a project's status when its actions change. Completing all actions SHALL NOT close the project, and closing a project SHALL NOT change its actions.

#### Scenario: Completed actions leave the project open

- **WHEN** every action of an active project becomes done
- **THEN** the project remains active and reports zero open actions

#### Scenario: Closing a project leaves actions unchanged

- **WHEN** the user changes a project to `done`
- **THEN** its action notes keep their current statuses

### Requirement: The Projects workspace reflects vault changes

After a scan, page save, action creation, status change, rename, or trash, the Projects workspace SHALL reflect the latest project and action state.

#### Scenario: Completing an action updates the count

- **WHEN** an open action becomes done
- **THEN** the project's open count decreases

#### Scenario: Adding an action updates the next action

- **WHEN** a new open action is linked to a project
- **THEN** the project row includes it and the next action is recomputed

#### Scenario: Trashing a project removes it

- **WHEN** a project is moved to trash
- **THEN** it disappears from the Projects workspace

#### Scenario: Viewing projects performs no write

- **WHEN** the Projects workspace is opened or refreshed
- **THEN** no note file is created, changed, or removed
