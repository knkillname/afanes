# Spec Delta

## ADDED Requirements

### Requirement: The project owner does not change workspace behavior

The project owner SHALL be display-only in the Projects workspace. Setting or clearing `owner` MUST
NOT change the project's status, group, due date, open-step count, next step, or review state. The
owner SHALL NOT be shown in the project row.

#### Scenario: Owner does not change the status

- **WHEN** an active project declares `owner: Sam Rivera`
- **THEN** it remains active

#### Scenario: Owner does not change the group

- **WHEN** a project with no status declares `owner: Sam Rivera`
- **THEN** it remains under Active

#### Scenario: Owner does not change the next step

- **WHEN** an open project declares an owner and has an unchecked first step
- **THEN** that step remains the next step

#### Scenario: Owner is absent from the project row

- **WHEN** the Projects workspace lists a project with an owner
- **THEN** the row shows no owner label

#### Scenario: Clearing the owner changes nothing else

- **WHEN** the user removes the owner from a project
- **THEN** its status, group, due date, open-step count, and next step are unchanged
