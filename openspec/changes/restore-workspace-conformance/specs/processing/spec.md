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

#### Scenario: Every fixed outcome is offered

- **WHEN** the Processing Wizard opens for a capture
- **THEN** the outcome list offers Trash, Later, Reference, Project, Log entry, Append step, and Done now

#### Scenario: A log entry is an explicit outcome

- **WHEN** the user chooses Log entry
- **THEN** the capture becomes a log entry and no other outcome is applied
