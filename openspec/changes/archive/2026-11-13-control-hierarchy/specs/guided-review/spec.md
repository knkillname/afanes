# Spec Delta

## MODIFIED Requirements

### Requirement: A stalled project can gain a next step

When a project has no open step, the review card SHALL offer adding a step, marking the project done, deferring it to `later`, or skipping. Adding a step SHALL require text and SHALL append a task list item to the project body, then refresh the project's next step.

#### Scenario: Add a next step

- **WHEN** the user supplies text for a stalled project's next step
- **THEN** a task list item is appended to the project body and the card shows it as the next step

#### Scenario: Cancel adding changes nothing

- **WHEN** the user cancels the next-step form
- **THEN** the project body is unchanged

#### Scenario: The add action is insensitive while blank

- **WHEN** the next-step text is empty or contains only whitespace
- **THEN** the Add Step action is insensitive and no step is added

#### Scenario: Blank text is rejected

- **WHEN** blank next-step text reaches the command without passing through the interface
- **THEN** no step is added and the error is reported

#### Scenario: Mark the project done

- **WHEN** the user confirms marking a stalled project done
- **THEN** the project status becomes `done` and it leaves the review queue

#### Scenario: Defer the project

- **WHEN** the user confirms deferring a stalled project
- **THEN** the project status becomes `later` and it remains open

#### Scenario: Skip leaves the project stalled

- **WHEN** the user skips a stalled project
- **THEN** the project keeps its status and remains in the next review's pending count
