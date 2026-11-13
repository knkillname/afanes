# Spec Delta

## MODIFIED Requirements

### Requirement: Browser creation writes immediately

Creating a reference from the browser SHALL write the note atomically and SHALL open it in edit mode. A blank name or a name collision MUST NOT create a note and SHALL be reported.

#### Scenario: Create writes and opens edit mode

- **WHEN** the user submits a valid name and card
- **THEN** the note is written and the page editor opens on it in edit mode

#### Scenario: Empty uses the general category

- **WHEN** the user creates with Empty
- **THEN** the note declares `category: general` and has no starter body

#### Scenario: The create action is insensitive while blank

- **WHEN** the name field is empty or contains only whitespace
- **THEN** the Create action is insensitive and no note is created

#### Scenario: A blank name is rejected

- **WHEN** a blank name reaches the command without passing through the interface
- **THEN** no note is created and the error is reported

#### Scenario: A collision is reported

- **WHEN** the name already belongs to a note in the same scheme
- **THEN** no note is created, no suffix is added, and the dialog reports the collision
