# Spec Delta

## MODIFIED Requirements

### Requirement: Inbox review reuses explicit processing

Each Inbox item in a review session SHALL open the existing processing flow, including the same
capture content, template card choices, and metadata inputs as processing from the Inbox. Applying an
outcome SHALL advance the session; cancelling SHALL leave the capture unchanged and keep the item
pending.

#### Scenario: Apply advances the session

- **WHEN** the user confirms a processing outcome for an Inbox item
- **THEN** the item is applied and the next review item is shown

#### Scenario: Cancel keeps the capture

- **WHEN** the user cancels processing for an Inbox item
- **THEN** the capture remains in `inbox/` and the session stays on that item or skips it

#### Scenario: Outcome is not inferred

- **WHEN** the capture text resembles an action, project, person, or date
- **THEN** the review does not choose an outcome or metadata from that text

#### Scenario: Template cards are available

- **WHEN** an Inbox item in a review session opens the Processing Wizard and the user chooses Reference or Later
- **THEN** the Template field lists every valid reference card and Empty
