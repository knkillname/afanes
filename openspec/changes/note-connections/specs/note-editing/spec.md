# Spec Delta

## ADDED Requirements

### Requirement: Read mode ends with the Connections section

Read mode SHALL place the Connections section after the rendered body of a parsed note. The section SHALL NOT appear
in edit mode or in raw rescue mode, and rendering it MUST NOT write to the vault or change the body text.

#### Scenario: Connections follow the body

- **WHEN** a parsed note with connections opens in read mode
- **THEN** the Connections section appears after the rendered body

#### Scenario: Edit mode hides connections

- **WHEN** the reader starts editing the open page
- **THEN** the Connections section is not shown

#### Scenario: Raw rescue hides connections

- **WHEN** a note opens in raw rescue mode
- **THEN** the Connections section is not shown

#### Scenario: Showing connections writes nothing

- **WHEN** read mode renders the section
- **THEN** no note file is created, changed, moved, or removed
