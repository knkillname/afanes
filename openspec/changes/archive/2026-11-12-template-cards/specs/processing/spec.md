# Spec Delta

## REMOVED Requirements

### Requirement: Reference outcome is uncategorized

**Reason**: Reference and Later now carry a user-chosen category supplied by a template card or by the Empty option.

**Migration**: Existing uncategorized references remain valid. Processing now writes `category: general` for Empty and the chosen card's category otherwise.

## MODIFIED Requirements

### Requirement: Processing preserves content

Processing SHALL preserve the capture text, newline style, and unknown frontmatter keys. It MAY append a template card's starter body below the capture text, and SHALL modify only the keys owned by the outcome. Append step SHALL modify only the capture and the target project body.

#### Scenario: Body is preserved

- **WHEN** a capture is processed
- **THEN** its original Markdown text remains a prefix of the body, apart from the classification

#### Scenario: A starter body is appended

- **WHEN** the chosen template card has a starter body
- **THEN** the body contains the capture text followed by the starter body

#### Scenario: Unknown keys are preserved

- **WHEN** the capture has an unknown frontmatter key
- **THEN** the key and value are written back unchanged

#### Scenario: Append preserves the target project

- **WHEN** a step is appended to a project
- **THEN** the rest of the project's frontmatter and body are unchanged

#### Scenario: Other notes are untouched

- **WHEN** a capture is processed without Append step
- **THEN** every other note's content is unchanged

## ADDED Requirements

### Requirement: Reference and Later use a template card

The Reference and Later outcomes SHALL ask the user to choose a template card or Empty. A card SHALL supply the category and starter body; Empty SHALL supply `general` and no starter body. Processing MUST NOT infer the card from the capture text.

#### Scenario: A card supplies the category

- **WHEN** the user chooses a card with `category: person`
- **THEN** the preview names the category and the note is filed under `reference/person/`

#### Scenario: Empty uses general

- **WHEN** the user chooses Empty
- **THEN** the preview names `general` and the note is filed under `reference/general/`

#### Scenario: The card is not inferred

- **WHEN** the capture text names a person or a place
- **THEN** processing does not choose a card from that text

#### Scenario: The preview names the starter body

- **WHEN** the chosen card has a starter body
- **THEN** the preview reports that the starter body will be added

### Requirement: Processing appends the starter body safely

When a card supplies a starter body, processing SHALL append it to the capture text in the same atomic write as the classification. A card that cannot be read SHALL abort the plan before any write.

#### Scenario: The body is appended in the atomic write

- **WHEN** the user confirms a card outcome
- **THEN** the category and the starter body are written together before the move

#### Scenario: Empty writes no starter body

- **WHEN** the user chooses Empty
- **THEN** the body contains only the capture text and the classification

#### Scenario: An unreadable card aborts

- **WHEN** the chosen card cannot be read at plan time
- **THEN** processing reports the failure and leaves the capture in the inbox

### Requirement: Processing finishes without opening the page editor

Applying a processing plan SHALL end in the success state. It MUST NOT open the created note in the page editor or navigate away from the processing or review flow.

#### Scenario: Success panel remains

- **WHEN** a plan is applied
- **THEN** the wizard shows the success state and no page editor opens

#### Scenario: Review moves on

- **WHEN** processing is part of a review session
- **THEN** the review can record the item and continue without opening the note

#### Scenario: The user can process the next capture

- **WHEN** the user finishes the success state
- **THEN** they return to the inbox or the next review item
