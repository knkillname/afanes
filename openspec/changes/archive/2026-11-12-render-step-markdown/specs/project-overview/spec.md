# Spec Delta

## ADDED Requirements

### Requirement: A project row renders its next step as Markdown

The next step shown by a project row SHALL be rendered as inline Markdown. Raw Markdown source MUST
NOT appear in the row. The status, due date, open-step count, and no-next-step label remain plain text.

#### Scenario: A link in the next step is rendered

- **WHEN** a project's next step contains `[Incident notes](<note:Incident notes>)`
- **THEN** the row shows `Next: Incident notes` and not the raw destination syntax

#### Scenario: Emphasis in the next step is rendered

- **WHEN** a project's next step contains `**Bold** step`
- **THEN** the row shows `Next: Bold step` with emphasis and not the asterisks

#### Scenario: A row without a next step stays plain

- **WHEN** a project has no open step
- **THEN** the row shows the plain no-next-step label

#### Scenario: Viewing a row writes nothing

- **WHEN** a project row is shown
- **THEN** no project file changes
