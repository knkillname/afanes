# Spec Delta

## ADDED Requirements

### Requirement: The References section offers a new-reference action

When a vault is open, the References section SHALL offer a New action. The action SHALL open a dialog that asks for a note name and a template card or Empty. The action MUST NOT be available without an open vault.

#### Scenario: The action is present

- **WHEN** the user views the References section
- **THEN** a New action is visible

#### Scenario: The dialog asks for a name and a card

- **WHEN** the user starts the New action
- **THEN** the dialog shows a name field, the valid cards, and Empty

#### Scenario: Invalid cards are reported

- **WHEN** the templates folder contains invalid cards
- **THEN** the dialog names them and still lists the valid cards

#### Scenario: No vault means no action

- **WHEN** no vault is open
- **THEN** the New action is not offered

### Requirement: Browser creation writes immediately

Creating a reference from the browser SHALL write the note atomically and SHALL open it in edit mode. A blank name or a name collision MUST NOT create a note and SHALL be reported.

#### Scenario: Create writes and opens edit mode

- **WHEN** the user submits a valid name and card
- **THEN** the note is written and the page editor opens on it in edit mode

#### Scenario: Empty uses the general category

- **WHEN** the user creates with Empty
- **THEN** the note declares `category: general` and has no starter body

#### Scenario: A blank name is rejected

- **WHEN** the user submits a blank name
- **THEN** no note is created and the dialog reports that a name is required

#### Scenario: A collision is reported

- **WHEN** the name already belongs to a note in the same scheme
- **THEN** no note is created, no suffix is added, and the dialog reports the collision

### Requirement: A browser-created reference appears in its group

After a browser creation succeeds, the application SHALL refresh the scan and SHALL show the new note under its category group. An active search query SHALL be cleared so the note is visible.

#### Scenario: The note appears under its category

- **WHEN** a note is created from a `person` card
- **THEN** it appears under the `person` group

#### Scenario: An active search is cleared

- **WHEN** the user creates a note while a search query is active
- **THEN** the query is cleared and the new note is visible

#### Scenario: A refresh failure is reported

- **WHEN** the note is created but the scan fails
- **THEN** the note remains and the application reports the refresh failure
